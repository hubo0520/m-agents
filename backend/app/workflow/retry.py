"""
工作流重试与降级策略

实现三级降级策略：
- L1: 自动重试（最多 3 次，指数退避）
- L2: LLM 节点降级到规则引擎
- L3: 创建人工处理任务，workflow 进入 PAUSED

同时提供重试装饰器供各节点使用。
"""
import time
import functools
import traceback
from datetime import datetime
from typing import Callable, Any

from app.workflow.state import GraphState, WorkflowStatus
from app.core.database import SessionLocal
from app.models.models import WorkflowRun, ApprovalTask, AuditLog


# ═══════════════════════════════════════════════════════════════
# L1: 自动重试装饰器
# ═══════════════════════════════════════════════════════════════

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """
    指数退避重试装饰器。

    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        print(f"⚠️ {func.__name__} 第 {attempt + 1} 次失败，{delay}s 后重试: {e}")
                        time.sleep(delay)
                    else:
                        print(f"❌ {func.__name__} {max_retries} 次重试全部失败: {e}")
            raise last_exception
        return wrapper
    return decorator


def retry_node(max_retries: int = 3, base_delay: float = 1.0):
    """
    LangGraph 节点级别的重试装饰器。

    节点函数签名: (state: GraphState) -> dict
    失败时返回包含 error_message 的 dict 而非抛出异常。
    """
    def decorator(node_fn: Callable[[GraphState], dict]) -> Callable[[GraphState], dict]:
        @functools.wraps(node_fn)
        def wrapper(state: GraphState) -> dict:
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    result = node_fn(state)
                    # 检查节点内部返回的错误
                    if result.get("error_message") and attempt < max_retries:
                        last_error = result["error_message"]
                        delay = base_delay * (2 ** attempt)
                        print(f"⚠️ 节点 {node_fn.__name__} 返回错误，{delay}s 后重试: {last_error}")
                        time.sleep(delay)
                        continue
                    return result
                except Exception as e:
                    last_error = str(e)
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        print(f"⚠️ 节点 {node_fn.__name__} 第 {attempt + 1} 次异常，{delay}s 后重试: {e}")
                        time.sleep(delay)
                    else:
                        print(f"❌ 节点 {node_fn.__name__} {max_retries} 次重试全部失败")

            # 所有重试失败，返回错误状态
            return {
                "error_message": f"节点 {node_fn.__name__} 重试 {max_retries} 次后仍失败: {last_error}",
                "current_status": WorkflowStatus.FAILED_RETRYABLE.value,
            }
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════
# L2: 规则引擎降级
# ═══════════════════════════════════════════════════════════════

def fallback_to_rules(state: GraphState, failed_node: str) -> dict:
    """
    当 LLM 节点重试全部失败后，降级到规则引擎。

    Args:
        state: 当前工作流状态
        failed_node: 失败的节点名称

    Returns:
        降级后的输出
    """
    print(f"🔄 节点 {failed_node} 降级到规则引擎模式")

    db = SessionLocal()
    try:
        from app.engine.rules import evaluate_risk, generate_rule_recommendations
        merchant_id = state.get("merchant_id", 0)

        if failed_node in ("diagnose_case",):
            # 降级为规则引擎风险评估
            risk_result = evaluate_risk(db, merchant_id)
            return {
                "diagnosis_output": {
                    "root_causes": [],
                    "business_summary": f"[规则降级] {risk_result.get('summary', 'Agent 分析失败，已回退到规则模式')}",
                    "key_factors": risk_result.get("factors", {}),
                    "risk_level": risk_result.get("risk_level", "medium"),
                    "manual_review_required": True,
                },
                "error_message": "",  # 清除错误，继续执行
            }

        elif failed_node in ("generate_recommendations",):
            # 降级为规则引擎生成建议
            recommendations = generate_rule_recommendations(db, merchant_id)
            return {
                "recommendation_output": {
                    "risk_level": "medium",
                    "recommendations": recommendations,
                },
                "error_message": "",
            }

        else:
            return {"error_message": f"节点 {failed_node} 无规则降级路径"}

    except Exception as e:
        print(f"❌ 规则引擎降级也失败: {e}")
        return {"error_message": f"规则降级失败: {str(e)}"}
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════
# L3: 人工接管
# ═══════════════════════════════════════════════════════════════

def create_manual_handoff(state: GraphState, failed_node: str, error_msg: str) -> dict:
    """
    创建人工接管任务，workflow 进入 PAUSED 状态。

    Args:
        state: 当前工作流状态
        failed_node: 失败的节点名称
        error_msg: 错误信息
    """
    db = SessionLocal()
    try:
        workflow_run_id = state.get("workflow_run_id")
        case_id = state.get("case_id", 0)

        # 创建人工接管审批任务
        task = ApprovalTask(
            workflow_run_id=workflow_run_id,
            case_id=case_id,
            approval_type="manual_handoff",
            assignee_role="risk_ops",
            status="PENDING",
            payload_json=f'{{"failed_node": "{failed_node}", "error": "{error_msg}"}}',
        )
        db.add(task)

        # 写入审计日志
        audit = AuditLog(
            entity_type="workflow_run",
            entity_id=workflow_run_id or 0,
            actor="system",
            action="manual_handoff_created",
            new_value=f'{{"failed_node": "{failed_node}", "error": "{error_msg}"}}',
        )
        db.add(audit)

        # 更新工作流状态
        if workflow_run_id:
            run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_run_id).first()
            if run:
                run.status = WorkflowStatus.PAUSED.value
                run.paused_at = datetime.utcnow()
                run.current_node = failed_node

        db.commit()
        print(f"🤚 已创建人工接管任务，workflow #{workflow_run_id} 进入 PAUSED")

        return {
            "current_status": WorkflowStatus.PAUSED.value,
            "should_pause": True,
            "error_message": f"已转人工处理: {error_msg}",
        }

    except Exception as e:
        db.rollback()
        return {
            "current_status": WorkflowStatus.FAILED_FINAL.value,
            "error_message": f"创建人工接管也失败: {str(e)}",
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════
# 三级降级调度器
# ═══════════════════════════════════════════════════════════════

def execute_with_fallback(
    state: GraphState,
    node_name: str,
    node_fn: Callable[[GraphState], dict],
    max_retries: int = 3,
    has_rule_fallback: bool = False,
) -> dict:
    """
    带三级降级的节点执行器。

    L1: 自动重试（最多 max_retries 次）
    L2: 降级到规则引擎（如果 has_rule_fallback=True）
    L3: 创建人工接管任务
    """
    # L1: 自动重试
    last_error = ""
    for attempt in range(max_retries + 1):
        try:
            result = node_fn(state)
            if not result.get("error_message"):
                return result
            last_error = result["error_message"]
            if attempt < max_retries:
                delay = 1.0 * (2 ** attempt)
                print(f"⚠️ L1: 节点 {node_name} 重试 {attempt + 1}/{max_retries}: {last_error}")
                time.sleep(delay)
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                delay = 1.0 * (2 ** attempt)
                time.sleep(delay)

    # L2: 规则引擎降级
    if has_rule_fallback:
        print(f"🔄 L2: 节点 {node_name} 降级到规则引擎")
        fallback_result = fallback_to_rules(state, node_name)
        if not fallback_result.get("error_message"):
            return fallback_result

    # L3: 人工接管
    print(f"🤚 L3: 节点 {node_name} 转人工接管")
    return create_manual_handoff(state, node_name, last_error)
