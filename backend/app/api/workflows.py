"""
工作流管理 API

提供 workflow 启动、恢复、重试、详情、轨迹等接口。
"""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import WorkflowRun, AgentRun, RiskCase


router = APIRouter(prefix="/api", tags=["工作流管理"])


class StartWorkflowRequest(BaseModel):
    case_id: int


# ───────────────── POST /api/workflows/start ─────────────────

@router.post("/workflows/start")
def start_workflow_api(req: StartWorkflowRequest, db: Session = Depends(get_db)):
    """启动新的工作流"""
    case = db.query(RiskCase).filter(RiskCase.id == req.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")

    from app.workflow.graph import start_workflow
    try:
        result = start_workflow(req.case_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ───────────────── POST /api/workflows/{run_id}/resume ─────────

@router.post("/workflows/{run_id}/resume")
def resume_workflow_api(run_id: int, db: Session = Depends(get_db)):
    """恢复暂停的工作流"""
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="工作流运行不存在")
    if run.status not in ("PAUSED", "PENDING_APPROVAL", "FAILED_RETRYABLE"):
        raise HTTPException(status_code=400, detail=f"状态为 {run.status}，无法恢复")

    from app.workflow.graph import resume_workflow
    try:
        result = resume_workflow(run_id, {"resumed_by_api": True})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ───────────────── POST /api/workflows/{run_id}/retry ─────────

@router.post("/workflows/{run_id}/retry")
def retry_workflow_api(run_id: int, db: Session = Depends(get_db)):
    """重试失败的工作流"""
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="工作流运行不存在")
    if run.status not in ("FAILED_RETRYABLE", "PAUSED"):
        raise HTTPException(status_code=400, detail=f"状态为 {run.status}，无法重试")

    # 重新启动工作流
    from app.workflow.graph import start_workflow
    try:
        # 标记旧 run 为终止
        run.status = "FAILED_FINAL"
        run.ended_at = datetime.utcnow()
        db.commit()

        # 创建新的 workflow run
        result = start_workflow(run.case_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ───────────────── GET /api/workflows/{run_id} ─────────────────

@router.get("/workflows/{run_id}")
def get_workflow_detail(run_id: int, db: Session = Depends(get_db)):
    """获取工作流详情"""
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="工作流运行不存在")

    agent_runs = db.query(AgentRun).filter(
        AgentRun.workflow_run_id == run_id,
    ).order_by(AgentRun.created_at.asc()).all()

    return {
        "id": run.id,
        "case_id": run.case_id,
        "graph_version": run.graph_version,
        "status": run.status,
        "current_node": run.current_node,
        "started_at": str(run.started_at) if run.started_at else None,
        "updated_at": str(run.updated_at) if run.updated_at else None,
        "paused_at": str(run.paused_at) if run.paused_at else None,
        "resumed_at": str(run.resumed_at) if run.resumed_at else None,
        "ended_at": str(run.ended_at) if run.ended_at else None,
        "agent_runs": [{
            "id": ar.id,
            "agent_name": ar.agent_name,
            "model_name": ar.model_name,
            "status": ar.status,
            "latency_ms": ar.latency_ms,
            "created_at": str(ar.created_at) if ar.created_at else None,
        } for ar in agent_runs],
    }


# ───────────────── GET /api/workflows/{run_id}/trace ─────────

@router.get("/workflows/{run_id}/trace")
def get_workflow_trace(run_id: int, db: Session = Depends(get_db)):
    """获取工作流执行轨迹"""
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="工作流运行不存在")

    agent_runs = db.query(AgentRun).filter(
        AgentRun.workflow_run_id == run_id,
    ).order_by(AgentRun.created_at.asc()).all()

    nodes = []
    for ar in agent_runs:
        nodes.append({
            "id": ar.id,
            "agent_name": ar.agent_name,
            "model_name": ar.model_name,
            "prompt_version": ar.prompt_version,
            "schema_version": ar.schema_version,
            "status": ar.status,
            "latency_ms": ar.latency_ms,
            "input_json": ar.input_json,
            "output_json": ar.output_json,
            "created_at": str(ar.created_at) if ar.created_at else None,
        })

    return {
        "workflow_run_id": run_id,
        "case_id": run.case_id,
        "status": run.status,
        "nodes": nodes,
        "total_latency_ms": sum(n["latency_ms"] or 0 for n in nodes),
    }


# ───────────────── GET /api/workflows ─────────────────

@router.get("/workflows")
def list_workflows(
    status: str = Query(None, description="状态筛选"),
    case_id: int = Query(None, description="案件 ID 筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取工作流列表"""
    query = db.query(WorkflowRun)
    if status:
        query = query.filter(WorkflowRun.status == status)
    if case_id:
        query = query.filter(WorkflowRun.case_id == case_id)

    total = query.count()
    items = query.order_by(WorkflowRun.started_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [{
            "id": r.id,
            "case_id": r.case_id,
            "graph_version": r.graph_version,
            "status": r.status,
            "current_node": r.current_node,
            "started_at": str(r.started_at) if r.started_at else None,
            "ended_at": str(r.ended_at) if r.ended_at else None,
        } for r in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ───────────────── GET /api/cases/{case_id}/latest-run ─────────

@router.get("/cases/{case_id}/latest-run")
def get_latest_run(case_id: int, db: Session = Depends(get_db)):
    """获取案件最新的 workflow run"""
    run = db.query(WorkflowRun).filter(
        WorkflowRun.case_id == case_id,
    ).order_by(WorkflowRun.started_at.desc()).first()

    if not run:
        raise HTTPException(status_code=404, detail="该案件无工作流运行记录")

    return {
        "id": run.id,
        "case_id": run.case_id,
        "status": run.status,
        "current_node": run.current_node,
        "started_at": str(run.started_at) if run.started_at else None,
        "ended_at": str(run.ended_at) if run.ended_at else None,
    }


# ───────────────── POST /api/cases/{case_id}/reopen ─────────

@router.post("/cases/{case_id}/reopen")
def reopen_case(case_id: int, db: Session = Depends(get_db)):
    """重开案件，创建新的 workflow_run"""
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")

    # 重置案件状态
    case.status = "NEW"
    case.updated_at = datetime.utcnow()
    db.commit()

    # 启动新的 workflow
    from app.workflow.graph import start_workflow
    try:
        result = start_workflow(case_id)
        return {"status": "ok", "case_id": case_id, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
