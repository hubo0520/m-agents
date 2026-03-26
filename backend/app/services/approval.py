"""
审批服务 — 状态流转校验与审计日志
"""
import json
from datetime import datetime
from app.core.utils import utc_now
from sqlalchemy.orm import Session
from loguru import logger

from app.models.models import RiskCase, Review, AuditLog, Recommendation
from app.services.task_generator import generate_tasks_for_case
from app.services.notification import NotificationService


# 合法状态流转
VALID_TRANSITIONS = {
    "NEW": ["ANALYZED"],
    "ANALYZED": ["PENDING_REVIEW"],
    "PENDING_REVIEW": ["APPROVED", "REJECTED"],
}


def write_audit_log(
    db: Session,
    entity_type: str,
    entity_id: int,
    actor: str,
    action: str,
    old_value: str = None,
    new_value: str = None,
):
    """写入审计日志"""
    log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        action=action,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(log)
    db.flush()
    return log


def transition_status(db: Session, case: RiskCase, new_status: str, actor: str = "system"):
    """执行状态流转并记录审计日志"""
    old_status = case.status
    allowed = VALID_TRANSITIONS.get(old_status, [])

    if new_status not in allowed:
        raise ValueError(
            f"非法状态流转: {old_status} → {new_status}，"
            f"允许: {allowed}"
        )

    case.status = new_status
    case.updated_at = utc_now()

    write_audit_log(
        db=db,
        entity_type="risk_case",
        entity_id=case.id,
        actor=actor,
        action=f"status_change",
        old_value=old_status,
        new_value=new_status,
    )


def review_case(
    db: Session,
    case_id: int,
    decision: str,
    comment: str,
    final_actions: list = None,
    reviewer_id: str = "operator",
) -> Review:
    """
    审批案件。
    - 驳回必须填理由
    - 融资类/反欺诈类动作强制备注
    - 原始 Agent 输出不可覆盖
    """
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        raise ValueError(f"案件 #{case_id} 不存在")

    # 校验: 必须处于 PENDING_REVIEW 状态
    if case.status != "PENDING_REVIEW":
        # 如果是 ANALYZED 状态，先转为 PENDING_REVIEW
        if case.status == "ANALYZED":
            transition_status(db, case, "PENDING_REVIEW", reviewer_id)
        else:
            raise ValueError(f"案件当前状态 {case.status}，无法审批")

    # 校验: 驳回必须填理由
    if decision == "reject" and (not comment or not comment.strip()):
        raise ValueError("驳回必须填写理由")

    # 校验: 融资类动作强制备注
    recommendations = db.query(Recommendation).filter(
        Recommendation.case_id == case_id
    ).all()
    has_finance_action = any(
        r.action_type in ("business_loan", "anomaly_review")
        for r in recommendations
    )
    if has_finance_action and decision in ("approve", "approve_with_changes"):
        if not comment or not comment.strip():
            raise ValueError("融资类/反欺诈类动作必须填写备注")

    # 映射 decision → 目标状态
    status_map = {
        "approve": "APPROVED",
        "approve_with_changes": "APPROVED",
        "reject": "REJECTED",
    }
    target_status = status_map.get(decision)
    if not target_status:
        raise ValueError(f"无效的审批决定: {decision}")

    # 创建 Review 记录 (原始 Agent 输出保留在 risk_cases.agent_output_json)
    review = Review(
        case_id=case_id,
        reviewer_id=reviewer_id,
        decision=decision,
        comment=comment,
        final_action_json=json.dumps(final_actions, ensure_ascii=False) if final_actions else None,
    )
    db.add(review)

    # 状态流转
    transition_status(db, case, target_status, reviewer_id)

    # V5: 审批结果通知 → 通知案件创建者
    try:
        # 此处使用 reviewer_id 作为审批人名称（实际可从 User 表查询 display_name）
        NotificationService.notify_approval_result(
            db=db,
            case_id=case_id,
            creator_user_id="1",  # TODO: 从 risk_case 关联查询实际创建者 ID
            decision=decision,
            reviewer_name=reviewer_id,
            comment=comment or "",
        )
    except Exception as e:
        logger.warning("审批结果通知发送失败（不影响审批）: %s", e)

    # 审计日志
    write_audit_log(
        db=db,
        entity_type="risk_case",
        entity_id=case_id,
        actor=reviewer_id,
        action=f"review_{decision}",
        old_value=json.dumps({"status": "PENDING_REVIEW"}, ensure_ascii=False),
        new_value=json.dumps({
            "status": target_status,
            "decision": decision,
            "comment": comment,
        }, ensure_ascii=False),
    )

    db.flush()

    # V2: 审批通过后自动触发任务生成
    if target_status == "APPROVED":
        try:
            tasks_generated = generate_tasks_for_case(db, case_id)
            if tasks_generated:
                write_audit_log(
                    db=db,
                    entity_type="risk_case",
                    entity_id=case_id,
                    actor="system",
                    action="task_generation_triggered",
                    new_value=f"审批通过后自动生成 {len(tasks_generated)} 条执行任务",
                )
        except Exception as e:
            # 任务生成失败不影响审批结果
            write_audit_log(
                db=db,
                entity_type="risk_case",
                entity_id=case_id,
                actor="system",
                action="task_generation_failed",
                new_value=str(e),
            )

    db.flush()
    return review
