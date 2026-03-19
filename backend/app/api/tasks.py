"""V2: 任务管理 API 路由"""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import (
    Merchant, RiskCase, FinancingApplication, Claim, ManualReview, AuditLog,
)
from app.schemas.schemas import TaskStatusUpdate
from app.services.approval import write_audit_log

router = APIRouter()

# ─────── 状态机定义 ───────
FINANCING_TRANSITIONS = {
    "DRAFT": ["PENDING_REVIEW"],
    "PENDING_REVIEW": ["APPROVED", "REJECTED"],
    "APPROVED": ["EXECUTING"],
    "EXECUTING": ["COMPLETED"],
}

CLAIM_TRANSITIONS = {
    "DRAFT": ["PENDING_REVIEW"],
    "PENDING_REVIEW": ["APPROVED", "REJECTED"],
    "APPROVED": ["EXECUTING"],
    "EXECUTING": ["COMPLETED"],
}

REVIEW_TRANSITIONS = {
    "PENDING": ["IN_PROGRESS"],
    "IN_PROGRESS": ["COMPLETED"],
    "COMPLETED": ["CLOSED"],
}


def _get_status_field(task_type: str) -> str:
    """获取不同任务类型的状态字段名"""
    if task_type == "financing":
        return "approval_status"
    elif task_type == "claim":
        return "claim_status"
    else:
        return "status"


def _get_transitions(task_type: str) -> dict:
    if task_type == "financing":
        return FINANCING_TRANSITIONS
    elif task_type == "claim":
        return CLAIM_TRANSITIONS
    else:
        return REVIEW_TRANSITIONS


# ─────── GET /api/tasks ─────────
@router.get("/tasks")
def list_tasks(
    task_type: str = None,
    status: str = None,
    assigned_to: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """统一任务列表查询，支持跨类型"""
    tasks = []

    # 是否需要查询各类型
    types_to_query = []
    if task_type:
        types_to_query = [task_type]
    else:
        types_to_query = ["financing", "claim", "manual_review"]

    # 融资申请
    if "financing" in types_to_query:
        query = db.query(FinancingApplication).join(
            Merchant, FinancingApplication.merchant_id == Merchant.id
        )
        if status:
            query = query.filter(FinancingApplication.approval_status == status)
        for fa in query.order_by(FinancingApplication.created_at.desc()).all():
            merchant = db.query(Merchant).filter(Merchant.id == fa.merchant_id).first()
            tasks.append({
                "task_id": fa.id,
                "task_type": "financing",
                "merchant_id": fa.merchant_id,
                "merchant_name": merchant.name if merchant else "未知",
                "case_id": fa.case_id,
                "status": fa.approval_status,
                "amount": fa.amount_requested,
                "assigned_to": None,
                "created_at": str(fa.created_at) if fa.created_at else None,
            })

    # 理赔申请
    if "claim" in types_to_query:
        query = db.query(Claim).join(Merchant, Claim.merchant_id == Merchant.id)
        if status:
            query = query.filter(Claim.claim_status == status)
        for cl in query.order_by(Claim.created_at.desc()).all():
            merchant = db.query(Merchant).filter(Merchant.id == cl.merchant_id).first()
            tasks.append({
                "task_id": cl.id,
                "task_type": "claim",
                "merchant_id": cl.merchant_id,
                "merchant_name": merchant.name if merchant else "未知",
                "case_id": cl.case_id,
                "status": cl.claim_status,
                "amount": cl.claim_amount,
                "assigned_to": None,
                "created_at": str(cl.created_at) if cl.created_at else None,
            })

    # 复核任务
    if "manual_review" in types_to_query:
        query = db.query(ManualReview).join(Merchant, ManualReview.merchant_id == Merchant.id)
        if status:
            query = query.filter(ManualReview.status == status)
        if assigned_to:
            query = query.filter(ManualReview.assigned_to == assigned_to)
        for mr in query.order_by(ManualReview.created_at.desc()).all():
            merchant = db.query(Merchant).filter(Merchant.id == mr.merchant_id).first()
            tasks.append({
                "task_id": mr.id,
                "task_type": "manual_review",
                "merchant_id": mr.merchant_id,
                "merchant_name": merchant.name if merchant else "未知",
                "case_id": mr.case_id,
                "status": mr.status,
                "amount": None,
                "assigned_to": mr.assigned_to,
                "created_at": str(mr.created_at) if mr.created_at else None,
            })

    # 按 created_at 排序
    tasks.sort(key=lambda x: x.get("created_at") or "", reverse=True)

    # 分页
    total = len(tasks)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "items": tasks[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ─────── GET /api/tasks/{task_type}/{task_id} ─────────
@router.get("/tasks/{task_type}/{task_id}")
def get_task_detail(task_type: str, task_id: int, db: Session = Depends(get_db)):
    """任务详情查询"""
    if task_type == "financing":
        task = db.query(FinancingApplication).filter(FinancingApplication.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="融资申请不存在")

        merchant = db.query(Merchant).filter(Merchant.id == task.merchant_id).first()
        case = db.query(RiskCase).filter(RiskCase.id == task.case_id).first()

        return {
            "id": task.id,
            "task_type": "financing",
            "merchant_id": task.merchant_id,
            "merchant_name": merchant.name if merchant else "未知",
            "case_id": task.case_id,
            "case_risk_level": case.risk_level if case else None,
            "recommendation_id": task.recommendation_id,
            "amount_requested": task.amount_requested,
            "loan_purpose": task.loan_purpose,
            "repayment_plan": json.loads(task.repayment_plan_json) if task.repayment_plan_json else None,
            "merchant_info_snapshot": json.loads(task.merchant_info_snapshot_json) if task.merchant_info_snapshot_json else None,
            "historical_settlement": json.loads(task.historical_settlement_json) if task.historical_settlement_json else None,
            "approval_status": task.approval_status,
            "reviewer_comment": task.reviewer_comment,
            "created_at": str(task.created_at) if task.created_at else None,
            "updated_at": str(task.updated_at) if task.updated_at else None,
        }

    elif task_type == "claim":
        task = db.query(Claim).filter(Claim.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="理赔申请不存在")

        merchant = db.query(Merchant).filter(Merchant.id == task.merchant_id).first()
        case = db.query(RiskCase).filter(RiskCase.id == task.case_id).first()

        return {
            "id": task.id,
            "task_type": "claim",
            "merchant_id": task.merchant_id,
            "merchant_name": merchant.name if merchant else "未知",
            "case_id": task.case_id,
            "case_risk_level": case.risk_level if case else None,
            "recommendation_id": task.recommendation_id,
            "policy_id": task.policy_id,
            "claim_amount": task.claim_amount,
            "claim_reason": task.claim_reason,
            "evidence_snapshot": json.loads(task.evidence_snapshot_json) if task.evidence_snapshot_json else None,
            "return_details": json.loads(task.return_details_json) if task.return_details_json else None,
            "claim_status": task.claim_status,
            "reviewer_comment": task.reviewer_comment,
            "created_at": str(task.created_at) if task.created_at else None,
            "updated_at": str(task.updated_at) if task.updated_at else None,
        }

    elif task_type == "manual_review":
        task = db.query(ManualReview).filter(ManualReview.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="复核任务不存在")

        merchant = db.query(Merchant).filter(Merchant.id == task.merchant_id).first()
        case = db.query(RiskCase).filter(RiskCase.id == task.case_id).first()

        return {
            "id": task.id,
            "task_type": "manual_review",
            "merchant_id": task.merchant_id,
            "merchant_name": merchant.name if merchant else "未知",
            "case_id": task.case_id,
            "case_risk_level": case.risk_level if case else None,
            "recommendation_id": task.recommendation_id,
            "task_type_detail": task.task_type,
            "review_reason": task.review_reason,
            "evidence_ids": json.loads(task.evidence_ids_json) if task.evidence_ids_json else [],
            "assigned_to": task.assigned_to,
            "status": task.status,
            "review_result": task.review_result,
            "reviewer_comment": task.reviewer_comment,
            "created_at": str(task.created_at) if task.created_at else None,
            "updated_at": str(task.updated_at) if task.updated_at else None,
            "completed_at": str(task.completed_at) if task.completed_at else None,
        }

    else:
        raise HTTPException(status_code=400, detail=f"不支持的任务类型: {task_type}")


# ─────── PUT /api/tasks/{task_type}/{task_id}/status ─────────
@router.put("/tasks/{task_type}/{task_id}/status")
def update_task_status(
    task_type: str,
    task_id: int,
    req: TaskStatusUpdate,
    db: Session = Depends(get_db),
):
    """任务状态更新，包含状态机合法性验证"""
    transitions = _get_transitions(task_type)

    if task_type == "financing":
        task = db.query(FinancingApplication).filter(FinancingApplication.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="融资申请不存在")
        current_status = task.approval_status
    elif task_type == "claim":
        task = db.query(Claim).filter(Claim.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="理赔申请不存在")
        current_status = task.claim_status
    elif task_type == "manual_review":
        task = db.query(ManualReview).filter(ManualReview.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="复核任务不存在")
        current_status = task.status
    else:
        raise HTTPException(status_code=400, detail=f"不支持的任务类型: {task_type}")

    # 验证状态流转合法性
    allowed = transitions.get(current_status, [])
    if req.new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"不允许的状态流转: {current_status} → {req.new_status}，允许: {allowed}",
        )

    # 更新状态
    old_status = current_status
    if task_type == "financing":
        task.approval_status = req.new_status
        if req.comment:
            task.reviewer_comment = req.comment
        task.updated_at = datetime.utcnow()
    elif task_type == "claim":
        task.claim_status = req.new_status
        if req.comment:
            task.reviewer_comment = req.comment
        task.updated_at = datetime.utcnow()
    elif task_type == "manual_review":
        task.status = req.new_status
        if req.comment:
            task.reviewer_comment = req.comment
        if req.new_status == "IN_PROGRESS" and task.assigned_to == "unassigned":
            task.assigned_to = req.reviewer_id
        if req.new_status == "COMPLETED":
            task.completed_at = datetime.utcnow()
            task.review_result = req.comment or "已完成"
        task.updated_at = datetime.utcnow()

    # 审计日志
    write_audit_log(
        db=db,
        entity_type=task_type,
        entity_id=task_id,
        actor=req.reviewer_id,
        action=f"status_change",
        old_value=old_status,
        new_value=req.new_status,
    )

    db.commit()
    return {
        "status": "success",
        "old_status": old_status,
        "new_status": req.new_status,
    }
