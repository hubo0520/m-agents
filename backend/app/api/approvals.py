"""
审批中心 API

提供审批任务的列表、详情、批准、驳回、修改后批准、批量审批等接口。
审批通过后自动触发 workflow resume。
"""
import json
from datetime import datetime
from app.core.utils import utc_now
from loguru import logger
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import ApprovalTask, WorkflowRun, AuditLog
from app.schemas.approval_schemas import (
    ApprovalTaskResponse, ApproveRequest, RejectRequest,
    ReviseAndApproveRequest, BatchApproveRequest,
)

router = APIRouter(prefix="/api/approvals", tags=["审批中心"])


# ───────────────── GET /api/approvals ─────────────────

@router.get("")
def list_approvals(
    status: str = Query(None, description="状态筛选: PENDING / APPROVED / REJECTED / OVERDUE"),
    approval_type: str = Query(None, description="审批类型筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取审批任务列表"""
    query = db.query(ApprovalTask)

    if status:
        query = query.filter(ApprovalTask.status == status)
    if approval_type:
        query = query.filter(ApprovalTask.approval_type == approval_type)

    total = query.count()
    items = query.order_by(ApprovalTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # 检查 SLA 超时
    now = utc_now()
    result_items = []
    for item in items:
        data = {
            "id": item.id,
            "workflow_run_id": item.workflow_run_id,
            "case_id": item.case_id,
            "approval_type": item.approval_type,
            "assignee_role": item.assignee_role,
            "status": item.status,
            "payload_json": item.payload_json,
            "reviewer": item.reviewer,
            "reviewed_at": str(item.reviewed_at) if item.reviewed_at else None,
            "comment": item.comment,
            "final_action_json": item.final_action_json,
            "created_at": str(item.created_at) if item.created_at else None,
            "due_at": str(item.due_at) if item.due_at else None,
        }
        # SLA 超时标记
        if item.status == "PENDING" and item.due_at and now > item.due_at:
            item.status = "OVERDUE"
            db.flush()
            data["status"] = "OVERDUE"
        result_items.append(data)

    db.commit()
    return {"items": result_items, "total": total, "page": page, "page_size": page_size}


# ───────────────── GET /api/approvals/{approval_id} ─────────────────

@router.get("/{approval_id}")
def get_approval_detail(approval_id: int, db: Session = Depends(get_db)):
    """获取审批详情"""
    task = db.query(ApprovalTask).filter(ApprovalTask.id == approval_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="审批任务不存在")

    return {
        "id": task.id,
        "workflow_run_id": task.workflow_run_id,
        "case_id": task.case_id,
        "approval_type": task.approval_type,
        "assignee_role": task.assignee_role,
        "status": task.status,
        "payload_json": task.payload_json,
        "reviewer": task.reviewer,
        "reviewed_at": str(task.reviewed_at) if task.reviewed_at else None,
        "comment": task.comment,
        "final_action_json": task.final_action_json,
        "created_at": str(task.created_at) if task.created_at else None,
        "due_at": str(task.due_at) if task.due_at else None,
    }


# ───────────────── POST /api/approvals/{approval_id}/approve ─────────────────

@router.post("/{approval_id}/approve")
def approve_task(approval_id: int, req: ApproveRequest, db: Session = Depends(get_db)):
    """批准审批任务"""
    task = db.query(ApprovalTask).filter(ApprovalTask.id == approval_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="审批任务不存在")
    if task.status not in ("PENDING", "OVERDUE"):
        raise HTTPException(status_code=400, detail=f"审批任务状态为 {task.status}，无法批准")

    task.status = "APPROVED"
    task.reviewer = req.reviewer_id
    task.reviewed_at = utc_now()
    task.comment = req.comment

    # 写入审计日志
    _log_audit(db, "approval_task", task.id, req.reviewer_id, "approve", task.status, "APPROVED")

    # 自动恢复关联 workflow
    _try_resume_workflow(db, task.workflow_run_id)

    db.commit()
    return {"status": "ok", "approval_id": approval_id, "new_status": "APPROVED"}


# ───────────────── POST /api/approvals/{approval_id}/reject ─────────────────

@router.post("/{approval_id}/reject")
def reject_task(approval_id: int, req: RejectRequest, db: Session = Depends(get_db)):
    """驳回审批任务"""
    task = db.query(ApprovalTask).filter(ApprovalTask.id == approval_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="审批任务不存在")
    if task.status not in ("PENDING", "OVERDUE"):
        raise HTTPException(status_code=400, detail=f"审批任务状态为 {task.status}，无法驳回")

    task.status = "REJECTED"
    task.reviewer = req.reviewer_id
    task.reviewed_at = utc_now()
    task.comment = req.comment

    _log_audit(db, "approval_task", task.id, req.reviewer_id, "reject", "PENDING", "REJECTED")

    # 更新关联 workflow 为 REJECTED
    if task.workflow_run_id:
        run = db.query(WorkflowRun).filter(WorkflowRun.id == task.workflow_run_id).first()
        if run:
            run.status = "REJECTED"
            run.ended_at = utc_now()

    db.commit()
    return {"status": "ok", "approval_id": approval_id, "new_status": "REJECTED"}


# ───────────────── POST /api/approvals/{approval_id}/revise-and-approve ─────

@router.post("/{approval_id}/revise-and-approve")
def revise_and_approve(approval_id: int, req: ReviseAndApproveRequest, db: Session = Depends(get_db)):
    """修改后批准"""
    task = db.query(ApprovalTask).filter(ApprovalTask.id == approval_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="审批任务不存在")
    if task.status not in ("PENDING", "OVERDUE"):
        raise HTTPException(status_code=400, detail=f"审批任务状态为 {task.status}，无法操作")

    task.status = "APPROVED"
    task.reviewer = req.reviewer_id
    task.reviewed_at = utc_now()
    task.comment = req.comment
    task.payload_json = json.dumps(req.revised_payload, ensure_ascii=False)
    task.final_action_json = json.dumps(req.revised_payload, ensure_ascii=False)

    _log_audit(db, "approval_task", task.id, req.reviewer_id, "revise_and_approve", "PENDING", "APPROVED")

    _try_resume_workflow(db, task.workflow_run_id)

    db.commit()
    return {"status": "ok", "approval_id": approval_id, "new_status": "APPROVED"}


# ───────────────── POST /api/approvals/batch ─────────────────

@router.post("/batch")
def batch_approve(req: BatchApproveRequest, db: Session = Depends(get_db)):
    """批量审批"""
    results = []
    for aid in req.approval_ids:
        task = db.query(ApprovalTask).filter(ApprovalTask.id == aid).first()
        if not task or task.status not in ("PENDING", "OVERDUE"):
            results.append({"approval_id": aid, "status": "skipped", "reason": "不存在或状态不允许"})
            continue

        if req.action == "approve":
            task.status = "APPROVED"
        elif req.action == "reject":
            task.status = "REJECTED"
        else:
            results.append({"approval_id": aid, "status": "error", "reason": f"未知操作: {req.action}"})
            continue

        task.reviewer = req.reviewer_id
        task.reviewed_at = utc_now()
        task.comment = req.comment

        _log_audit(db, "approval_task", task.id, req.reviewer_id, req.action, "PENDING", task.status)

        if req.action == "approve":
            _try_resume_workflow(db, task.workflow_run_id)
        elif req.action == "reject" and task.workflow_run_id:
            run = db.query(WorkflowRun).filter(WorkflowRun.id == task.workflow_run_id).first()
            if run:
                run.status = "REJECTED"
                run.ended_at = utc_now()

        results.append({"approval_id": aid, "status": "ok", "new_status": task.status})

    db.commit()
    return {"results": results}


# ───────────────── 辅助函数 ─────────────────

def _log_audit(db: Session, entity_type: str, entity_id: int, actor: str, action: str, old_val: str, new_val: str):
    """写入审计日志"""
    db.add(AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        action=action,
        old_value=old_val,
        new_value=new_val,
    ))


def _try_resume_workflow(db: Session, workflow_run_id: int):
    """尝试恢复暂停的 workflow"""
    if not workflow_run_id:
        return

    run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_run_id).first()
    if not run or run.status not in ("PAUSED", "PENDING_APPROVAL"):
        return

    # 检查该 workflow 的所有审批任务是否都已完成
    pending_tasks = db.query(ApprovalTask).filter(
        ApprovalTask.workflow_run_id == workflow_run_id,
        ApprovalTask.status == "PENDING",
    ).count()

    if pending_tasks == 0:
        # 所有审批完成，触发 workflow resume
        run.status = "RESUMED"
        run.resumed_at = utc_now()
        run.current_node = "execute_actions"
        db.flush()

        # 异步触发 workflow 恢复（简化为同步调用）
        try:
            from app.workflow.graph import resume_workflow
            resume_workflow(workflow_run_id, {"all_approved": True})
        except Exception as e:
            logger.warning("⚠️ Workflow 恢复失败 | workflow_run_id={} | error={}", workflow_run_id, e)
