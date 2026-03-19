"""
LangGraph 工作流图定义

使用 LangGraph StateGraph 构建多 Agent 编排主流程图。
"""
import json
import logging
from datetime import datetime
from typing import Literal

logger = logging.getLogger(__name__)

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

    # run_guardrails → 条件路由
    graph.add_conditional_edges("run_guardrails", route_after_guardrails, {
        "create_approval_tasks": "create_approval_tasks",
        "execute_actions": "execute_actions",
        "write_audit_log": "write_audit_log",
    })

    # create_approval_tasks → wait_for_approval
    graph.add_edge("create_approval_tasks", "wait_for_approval")

    # wait_for_approval → 条件路由
    graph.add_conditional_edges("wait_for_approval", route_after_approval, {
        "execute_actions": "execute_actions",
        "write_audit_log": "write_audit_log",
        END: END,
    })

    # execute_actions → wait_external_callback → finalize_summary
    graph.add_edge("execute_actions", "wait_external_callback")
    graph.add_edge("wait_external_callback", "finalize_summary")

    # finalize_summary → write_audit_log
    graph.add_edge("finalize_summary", "write_audit_log")

    # write_audit_log → END
    graph.add_edge("write_audit_log", END)

    return graph.compile()


# ═══════════════════════════════════════════════════════════════
# 简化执行器（不依赖 LangGraph）
# ═══════════════════════════════════════════════════════════════

def _run_sequential(state: GraphState) -> GraphState:
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
        ("create_approval_tasks", create_approval_tasks),
        ("finalize_summary", finalize_summary),
        ("write_audit_log", write_audit_log),
    ]

    for node_name, node_fn in node_sequence:
        try:
            logger.info("▶ 执行节点: %s | case_id=%s", node_name, state.get("case_id"))
            start = __import__("time").time()
            result = node_fn(state)
            elapsed_ms = int((__import__("time").time() - start) * 1000)
            state.update(result)
            logger.info("✔ 节点完成: %s | %dms | status=%s", node_name, elapsed_ms, state.get("current_status"))

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


def start_workflow(case_id: int) -> dict:
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
            final_state = _run_sequential(initial_state)

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
        run.resumed_at = datetime.utcnow()
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