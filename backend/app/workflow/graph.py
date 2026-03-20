"""
LangGraph 工作流图定义

使用 LangGraph StateGraph 构建多 Agent 编排主流程图。
"""
import json
from datetime import datetime
from app.core.utils import utc_now
from typing import Literal
from loguru import logger

from app.workflow.state import GraphState, WorkflowStatus
from app.workflow.nodes import (
    load_case_context,
    triage_case,
    compute_metrics,
    forecast_gap,
    diagnose_case,
    collect_evidence,
    generate_recommendations,
    run_guardrails,
    create_approval_tasks,
    wait_for_approval,
    execute_actions,
    wait_external_callback,
    finalize_summary,
    write_audit_log,
)
from app.core.database import SessionLocal
from app.models.models import WorkflowRun, RiskCase

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    # Fallback: 不使用 LangGraph 时提供简化实现
    StateGraph = None
    END = "__end__"


# ═══════════════════════════════════════════════════════════════
# 条件分支路由函数
# ═══════════════════════════════════════════════════════════════

def route_after_triage(state: GraphState) -> str:
    """根据 triage 输出决定走哪条子路径"""
    triage = state.get("triage_output", {})
    case_type = triage.get("case_type", "cash_gap")
    error = state.get("error_message", "")

    if error:
        return "write_audit_log"

    # 所有路径都先计算指标
    return "compute_metrics"


def route_after_guardrails(state: GraphState) -> str:
    """根据合规校验结果决定是否进入审批"""
    guard = state.get("guard_output", {})
    error = state.get("error_message", "")

    if error:
        return "write_audit_log"

    if not guard.get("passed", True) and guard.get("blocked_actions"):
        # 有被阻断的动作但仍有通过的建议 → 进入审批
        return "create_approval_tasks"

    next_state = guard.get("next_state", "PENDING_APPROVAL")
    if next_state == "EXECUTING":
        return "execute_actions"
    elif next_state == "BLOCKED_BY_GUARD":
        return "write_audit_log"
    else:
        return "create_approval_tasks"


def route_after_approval(state: GraphState) -> str:
    """根据审批结果决定是否执行"""
    current_status = state.get("current_status", "")
    should_pause = state.get("should_pause", False)

    if should_pause:
        # 暂停等待审批 — 在实际 LangGraph 实现中使用 interrupt
        return END

    if current_status == WorkflowStatus.REJECTED.value:
        return "write_audit_log"

    return "execute_actions"


def route_after_error(state: GraphState) -> str:
    """错误路由"""
    if state.get("error_message"):
        return "write_audit_log"
    return "finalize_summary"


# ═══════════════════════════════════════════════════════════════
# Graph 构建
# ═══════════════════════════════════════════════════════════════

def build_graph():
    """构建 LangGraph 工作流图"""
    if not LANGGRAPH_AVAILABLE:
        return None

    graph = StateGraph(GraphState)

    # 添加所有节点
    graph.add_node("load_case_context", load_case_context)
    graph.add_node("triage_case", triage_case)
    graph.add_node("compute_metrics", compute_metrics)
    graph.add_node("forecast_gap", forecast_gap)
    graph.add_node("collect_evidence", collect_evidence)
    graph.add_node("diagnose_case", diagnose_case)
    graph.add_node("generate_recommendations", generate_recommendations)
    graph.add_node("run_guardrails", run_guardrails)
    graph.add_node("create_approval_tasks", create_approval_tasks)
    graph.add_node("wait_for_approval", wait_for_approval)
    graph.add_node("execute_actions", execute_actions)
    graph.add_node("wait_external_callback", wait_external_callback)
    graph.add_node("finalize_summary", finalize_summary)
    graph.add_node("write_audit_log", write_audit_log)

    # 定义边
    graph.set_entry_point("load_case_context")

    # load_case_context → triage_case
    graph.add_edge("load_case_context", "triage_case")

    # triage_case → compute_metrics（条件路由）
    graph.add_conditional_edges("triage_case", route_after_triage, {
        "compute_metrics": "compute_metrics",
        "write_audit_log": "write_audit_log",
    })

    # compute_metrics → forecast_gap → collect_evidence → diagnose_case
    graph.add_edge("compute_metrics", "forecast_gap")
    graph.add_edge("forecast_gap", "collect_evidence")
    graph.add_edge("collect_evidence", "diagnose_case")

    # diagnose_case → generate_recommendations
    graph.add_edge("diagnose_case", "generate_recommendations")

    # generate_recommendations → run_guardrails
    graph.add_edge("generate_recommendations", "run_guardrails")

    # run_guardrails → finalize_summary（先生成总结，再创建审批）
    graph.add_edge("run_guardrails", "finalize_summary")

    # finalize_summary → create_approval_tasks
    graph.add_edge("finalize_summary", "create_approval_tasks")

    # create_approval_tasks → wait_for_approval
    graph.add_edge("create_approval_tasks", "wait_for_approval")

    # wait_for_approval → 条件路由
    graph.add_conditional_edges("wait_for_approval", route_after_approval, {
        "execute_actions": "execute_actions",
        "write_audit_log": "write_audit_log",
        END: END,
    })

    # execute_actions → wait_external_callback → write_audit_log
    graph.add_edge("execute_actions", "wait_external_callback")
    graph.add_edge("wait_external_callback", "write_audit_log")

    # write_audit_log → END
    graph.add_edge("write_audit_log", END)

    return graph.compile()


# ═══════════════════════════════════════════════════════════════
# 简化执行器（不依赖 LangGraph）
# ═══════════════════════════════════════════════════════════════

# V3 工作流节点中文名映射
V3_NODE_NAMES = {
    "load_case_context": "加载案件上下文",
    "triage_case": "案件分诊",
    "compute_metrics": "计算商家指标",
    "forecast_gap": "现金缺口预测",
    "collect_evidence": "收集证据",
    "diagnose_case": "诊断根因",
    "generate_recommendations": "生成建议",
    "run_guardrails": "合规校验",
    "finalize_summary": "生成分析总结",
    "create_approval_tasks": "创建审批任务",
    "write_audit_log": "写入审计日志",
}


def _persist_step_progress(
    case_id, step: str, step_name: str, step_index: int, total_steps: int,
    status: str, elapsed_ms: int = 0, summary: str = "",
    llm_input_summary: str = "", llm_output_summary: str = "",
):
    """
    将工作流步骤进度持久化到 RiskCase.analysis_progress_json。
    使用独立 session，不影响主工作流事务。
    """
    if not case_id:
        return
    try:
        import json
        persist_db = SessionLocal()
        try:
            case = persist_db.query(RiskCase).filter(RiskCase.id == case_id).first()
            if not case:
                return

            progress = []
            if case.analysis_progress_json:
                progress = json.loads(case.analysis_progress_json)

            event_data = {
                "step": step, "step_name": step_name,
                "step_index": step_index, "total_steps": total_steps,
                "status": status, "elapsed_ms": elapsed_ms, "summary": summary,
            }
            # 附加 LLM 摘要字段（仅在有数据时）
            if llm_input_summary:
                event_data["llm_input_summary"] = llm_input_summary
            if llm_output_summary:
                event_data["llm_output_summary"] = llm_output_summary

            # 更新或追加（合并已有数据，保留 LLM 摘要字段不被覆盖）
            found = False
            for i, s in enumerate(progress):
                if s.get("step") == step:
                    # 保留已有的 LLM 摘要字段
                    merged = {**s, **event_data}
                    progress[i] = merged
                    found = True
                    break
            if not found:
                progress.append(event_data)

            case.analysis_progress_json = json.dumps(progress, ensure_ascii=False)
            persist_db.commit()
        finally:
            persist_db.close()
    except Exception as e:
        logger.warning("持久化步骤进度失败（不影响工作流）: %s", e)


def _run_sequential(state: GraphState, on_progress=None, on_llm_event=None) -> GraphState:
    """按顺序执行所有节点（LangGraph 不可用时的 fallback）"""
    node_sequence = [
        ("load_case_context", load_case_context),
        ("triage_case", triage_case),
        ("compute_metrics", compute_metrics),
        ("forecast_gap", forecast_gap),
        ("collect_evidence", collect_evidence),
        ("diagnose_case", diagnose_case),
        ("generate_recommendations", generate_recommendations),
        ("run_guardrails", run_guardrails),
        ("finalize_summary", finalize_summary),
        ("create_approval_tasks", create_approval_tasks),
        ("write_audit_log", write_audit_log),
    ]

    total_nodes = len(node_sequence)

    # 缓存每个步骤的 LLM 摘要数据（避免在 on_llm_event 中直接写库导致 SQLite 锁冲突）
    _llm_summaries: dict = {}  # {step: {"input": str, "output": str}}
    # 用于 llm_chunk 节流持久化：累积 chunk 内容，每 N 个 chunk 或每隔一定时间写一次库
    _llm_chunk_count: dict = {}  # {step: int}  — 记录未持久化的 chunk 数量
    _LLM_PERSIST_INTERVAL = 5  # 每累积 5 个 chunk 持久化一次

    def _persist_llm_interim(step_name_key: str, step_display_name: str, step_idx: int):
        """将当前 LLM 中间数据持久化到数据库（用于刷新恢复）"""
        summary = _llm_summaries.get(step_name_key)
        if not summary:
            return
        try:
            _persist_step_progress(
                state.get("case_id"), step_name_key, step_display_name,
                step_idx, total_nodes, "running", 0, "",
                llm_input_summary=summary.get("input", ""),
                llm_output_summary=summary.get("output", ""),
            )
        except Exception:
            pass

    def _wrapped_on_llm_event(llm_evt):
        """包装 on_llm_event：在转发给 SSE 队列的同时，缓存 LLM 摘要到内存并定期持久化"""
        # 转发原始事件给 SSE 推送
        if on_llm_event:
            on_llm_event(llm_evt)
        # 缓存 LLM 摘要数据
        if llm_evt.event_type == "llm_input":
            _llm_summaries[llm_evt.step] = {
                "input": (llm_evt.system_prompt[:200] + "..." if len(llm_evt.system_prompt or "") > 200 else (llm_evt.system_prompt or "")),
                "output": "",
            }
            _llm_chunk_count[llm_evt.step] = 0
            # 立即持久化输入 prompt，刷新后可以立即看到
            step_idx_val = next((i + 1 for i, (n, _) in enumerate(node_sequence) if n == llm_evt.step), 0)
            step_display = V3_NODE_NAMES.get(llm_evt.step, llm_evt.step)
            _persist_llm_interim(llm_evt.step, step_display, step_idx_val)
        elif llm_evt.event_type == "llm_chunk":
            # 累积 chunk 内容
            if llm_evt.step in _llm_summaries:
                _llm_summaries[llm_evt.step]["output"] += llm_evt.content or ""
                _llm_chunk_count[llm_evt.step] = _llm_chunk_count.get(llm_evt.step, 0) + 1
                # 节流持久化：每 N 个 chunk 写一次库
                if _llm_chunk_count[llm_evt.step] >= _LLM_PERSIST_INTERVAL:
                    _llm_chunk_count[llm_evt.step] = 0
                    step_idx_val = next((i + 1 for i, (n, _) in enumerate(node_sequence) if n == llm_evt.step), 0)
                    step_display = V3_NODE_NAMES.get(llm_evt.step, llm_evt.step)
                    _persist_llm_interim(llm_evt.step, step_display, step_idx_val)
        elif llm_evt.event_type == "llm_done":
            if llm_evt.step in _llm_summaries:
                _llm_summaries[llm_evt.step]["output"] = llm_evt.content[:500] if llm_evt.content else ""
            else:
                _llm_summaries[llm_evt.step] = {
                    "input": "",
                    "output": llm_evt.content[:500] if llm_evt.content else "",
                }

    for idx, (node_name, node_fn) in enumerate(node_sequence):
        step_index = idx + 1
        step_name = V3_NODE_NAMES.get(node_name, node_name)

        # 发送 running 事件
        if on_progress:
            try:
                from app.agents.orchestrator import AnalysisProgressEvent
                on_progress(AnalysisProgressEvent(
                    step=node_name, step_name=step_name,
                    step_index=step_index, total_steps=total_nodes,
                    status="running",
                ))
            except Exception:
                pass

        # 持久化 running 状态到数据库
        _persist_step_progress(state.get("case_id"), node_name, step_name, step_index, total_nodes, "running")

        try:
            logger.info("▶ 执行节点: %s | case_id=%s", node_name, state.get("case_id"))
            start = __import__("time").time()
            # 对使用 LLM 的节点注入 on_llm_event 回调
            llm_nodes = ("diagnose_case", "generate_recommendations", "finalize_summary", "run_guardrails")
            if node_name in llm_nodes and on_llm_event:
                state["_on_llm_event"] = _wrapped_on_llm_event
            result = node_fn(state)
            # 清理临时注入的回调
            state.pop("_on_llm_event", None)
            elapsed_ms = int((__import__("time").time() - start) * 1000)
            state.update(result)
            logger.info("✔ 节点完成: %s | %dms | status=%s", node_name, elapsed_ms, state.get("current_status"))

            # 发送 completed 事件
            if on_progress:
                try:
                    from app.agents.orchestrator import AnalysisProgressEvent
                    on_progress(AnalysisProgressEvent(
                        step=node_name, step_name=step_name,
                        step_index=step_index, total_steps=total_nodes,
                        status="completed", elapsed_ms=elapsed_ms,
                        summary=f"节点 {step_name} 执行完成",
                    ))
                except Exception:
                    pass

            # 持久化 completed 状态到数据库（同时写入 LLM 摘要数据）
            llm_summary = _llm_summaries.pop(node_name, None)
            _persist_step_progress(
                state.get("case_id"), node_name, step_name, step_index, total_nodes,
                "completed", elapsed_ms, f"节点 {step_name} 执行完成",
                llm_input_summary=llm_summary["input"] if llm_summary else "",
                llm_output_summary=llm_summary["output"] if llm_summary else "",
            )

            # 检查是否需要暂停
            if state.get("should_pause"):
                logger.info("⏸ 工作流暂停于节点: %s", node_name)
                break

            # 检查是否有错误
            if state.get("error_message"):
                logger.error("✘ 节点 %s 返回错误: %s", node_name, state.get("error_message"))
                # 直接跳到 write_audit_log
                audit_result = write_audit_log(state)
                state.update(audit_result)
                break
        except Exception as e:
            logger.exception("✘ 节点 %s 异常崩溃 | case_id=%s", node_name, state.get("case_id"))
            state["error_message"] = f"节点 {node_name} 执行失败: {str(e)}"
            state["current_status"] = WorkflowStatus.FAILED_RETRYABLE.value
            # 发送 error 事件
            if on_progress:
                try:
                    from app.agents.orchestrator import AnalysisProgressEvent
                    on_progress(AnalysisProgressEvent(
                        step=node_name, step_name=step_name,
                        step_index=step_index, total_steps=total_nodes,
                        status="error", summary=str(e),
                    ))
                except Exception:
                    pass
            # 持久化 error 状态到数据库
            _persist_step_progress(state.get("case_id"), node_name, step_name, step_index, total_nodes, "error", 0, str(e))
            write_audit_log(state)
            break

    return state


# ═══════════════════════════════════════════════════════════════
# 公开 API
# ═══════════════════════════════════════════════════════════════

# 编译后的 graph 实例
_compiled_graph = None


def get_graph():
    """获取编译后的 graph（惰性初始化）"""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def start_workflow(case_id: int, on_progress=None, on_llm_event=None) -> dict:
    """
    启动新的工作流。

    1. 创建 workflow_run 记录
    2. 构建初始 state
    3. 执行 graph
    4. 返回最终 state
    """
    db = SessionLocal()
    try:
        # 验证案件存在
        case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
        if not case:
            raise ValueError(f"案件 #{case_id} 不存在")

        # 创建 workflow_run 记录
        workflow_run = WorkflowRun(
            case_id=case_id,
            graph_version="v3.0",
            status=WorkflowStatus.NEW.value,
            current_node="load_case_context",
        )
        db.add(workflow_run)
        db.commit()
        db.refresh(workflow_run)

        logger.info("🚀 启动工作流 | case_id=%s | run_id=%s", case_id, workflow_run.id)

        # 构建初始 state
        initial_state: GraphState = {
            "case_id": case_id,
            "merchant_id": case.merchant_id,
            "workflow_run_id": workflow_run.id,
            "current_status": WorkflowStatus.NEW.value,
            "should_pause": False,
            "error_message": "",
        }

        # 执行 graph
        graph = get_graph()
        if graph:
            logger.info("📊 使用 LangGraph 执行工作流")
            final_state = graph.invoke(initial_state)
        else:
            logger.info("📊 LangGraph 不可用，使用顺序执行 fallback")
            final_state = _run_sequential(initial_state, on_progress=on_progress, on_llm_event=on_llm_event)

        logger.info("✅ V3 工作流完成: run_id=%s, status=%s",
                     workflow_run.id, final_state.get("current_status", "UNKNOWN"))

        return {
            "workflow_run_id": workflow_run.id,
            "status": final_state.get("current_status", "COMPLETED"),
            "summary": final_state.get("summary_output", {}),
        }

    except Exception as e:
        db.rollback()
        logger.exception("💥 工作流启动失败 | case_id=%s", case_id)
        raise
    finally:
        db.close()


def resume_workflow(workflow_run_id: int, approval_results: dict = None) -> dict:
    """
    恢复暂停的工作流。

    1. 读取 workflow_run 记录
    2. 从暂停点构建 state
    3. 继续执行
    """
    db = SessionLocal()
    try:
        run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_run_id).first()
        if not run:
            raise ValueError(f"工作流运行 #{workflow_run_id} 不存在")

        if run.status not in (WorkflowStatus.PAUSED.value, WorkflowStatus.FAILED_RETRYABLE.value):
            raise ValueError(f"工作流运行 #{workflow_run_id} 状态为 {run.status}，无法恢复")

        # 更新为恢复中
        run.status = WorkflowStatus.RESUMED.value
        run.resumed_at = utc_now()
        run.current_node = "execute_actions"
        db.commit()

        case = db.query(RiskCase).filter(RiskCase.id == run.case_id).first()

        # 构建恢复后的 state — 简化版本，直接从 execute_actions 开始
        state: GraphState = {
            "case_id": run.case_id,
            "merchant_id": case.merchant_id if case else 0,
            "workflow_run_id": workflow_run_id,
            "approval_results": approval_results or {},
            "current_status": WorkflowStatus.EXECUTING.value,
            "should_pause": False,
            "error_message": "",
        }

        # 从暂停点继续执行
        from app.workflow.nodes import execute_actions, wait_external_callback, finalize_summary, write_audit_log
        for node_fn in [execute_actions, wait_external_callback, finalize_summary, write_audit_log]:
            result = node_fn(state)
            state.update(result)
            if state.get("error_message"):
                break

        return {
            "workflow_run_id": workflow_run_id,
            "status": state.get("current_status", "COMPLETED"),
            "summary": state.get("summary_output", {}),
        }

    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()