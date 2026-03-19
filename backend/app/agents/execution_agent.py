"""
Execution Agent — 审批通过后执行动作

在审批通过后调用工具/连接器执行动作（创建融资草稿/理赔草稿/复核任务/回款加速任务）。
"""
import json
from datetime import datetime
from sqlalchemy.orm import Session

from app.agents.schemas import ActionResult


# 动作执行器注册表
ACTION_EXECUTORS = {}


def register_executor(action_type: str):
    """动作执行器注册装饰器"""
    def decorator(func):
        ACTION_EXECUTORS[action_type] = func
        return func
    return decorator


@register_executor("advance_settlement")
def execute_advance_settlement(
    db: Session, case_id: int, merchant_id: int, payload: dict
) -> ActionResult:
    """执行回款加速"""
    # 调用工具注册中心的连接器
    from app.services.tool_registry import invoke_tool
    result = invoke_tool(
        db=db,
        tool_name="submit_advance_settlement",
        workflow_run_id=payload.get("workflow_run_id"),
        input_data={
            "merchant_id": merchant_id,
            "case_id": case_id,
            "amount": payload.get("amount", 0),
        },
    )
    return ActionResult(
        action_type="advance_settlement",
        status="executed" if result.get("success") else "failed",
        detail=result.get("message", "回款加速申请已提交"),
    )


@register_executor("business_loan")
def execute_business_loan(
    db: Session, case_id: int, merchant_id: int, payload: dict
) -> ActionResult:
    """执行经营贷草稿创建"""
    from app.services.task_generator import generate_tasks_for_case
    try:
        tasks = generate_tasks_for_case(db, case_id)
        return ActionResult(
            action_type="business_loan",
            status="executed",
            detail=f"经营贷草稿已创建，共生成 {len(tasks)} 个任务",
        )
    except Exception as e:
        return ActionResult(
            action_type="business_loan",
            status="failed",
            detail=f"经营贷草稿创建失败: {str(e)}",
        )


@register_executor("anomaly_review")
def execute_anomaly_review(
    db: Session, case_id: int, merchant_id: int, payload: dict
) -> ActionResult:
    """执行人工复核任务创建"""
    from app.services.task_generator import generate_tasks_for_case
    try:
        tasks = generate_tasks_for_case(db, case_id)
        return ActionResult(
            action_type="anomaly_review",
            status="executed",
            detail=f"人工复核任务已创建，共 {len(tasks)} 个任务",
        )
    except Exception as e:
        return ActionResult(
            action_type="anomaly_review",
            status="failed",
            detail=f"复核任务创建失败: {str(e)}",
        )


@register_executor("insurance_adjust")
def execute_insurance_adjust(
    db: Session, case_id: int, merchant_id: int, payload: dict
) -> ActionResult:
    """执行保险策略调整"""
    return ActionResult(
        action_type="insurance_adjust",
        status="executed",
        detail="保险策略调整建议已记录",
    )


@register_executor("claim_submission")
def execute_claim_submission(
    db: Session, case_id: int, merchant_id: int, payload: dict
) -> ActionResult:
    """执行理赔草稿提交"""
    from app.services.task_generator import generate_tasks_for_case
    try:
        tasks = generate_tasks_for_case(db, case_id)
        return ActionResult(
            action_type="claim_submission",
            status="executed",
            detail=f"理赔草稿已创建，共 {len(tasks)} 个任务",
        )
    except Exception as e:
        return ActionResult(
            action_type="claim_submission",
            status="failed",
            detail=f"理赔草稿创建失败: {str(e)}",
        )


def run_execution(
    db: Session,
    case_id: int,
    merchant_id: int,
    approved_actions: list,
    workflow_run_id: int = None,
) -> list:
    """
    执行审批通过后的动作列表。

    Args:
        db: 数据库会话
        case_id: 案件 ID
        merchant_id: 商家 ID
        approved_actions: 审批通过的动作列表，每个包含 action_type 和 payload
        workflow_run_id: 工作流运行 ID

    Returns:
        ActionResult 列表
    """
    results = []

    for action in approved_actions:
        action_type = action.get("action_type", "")
        payload = action.get("payload", {})
        payload["workflow_run_id"] = workflow_run_id

        executor = ACTION_EXECUTORS.get(action_type)
        if executor:
            try:
                result = executor(db, case_id, merchant_id, payload)
                results.append(result)
            except Exception as e:
                results.append(ActionResult(
                    action_type=action_type,
                    status="failed",
                    detail=f"执行失败: {str(e)}",
                ))
        else:
            results.append(ActionResult(
                action_type=action_type,
                status="failed",
                detail=f"未知动作类型: {action_type}",
            ))

    return results
