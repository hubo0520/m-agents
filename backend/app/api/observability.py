"""
可观测面板 API — Agent 运行指标统计
"""
from datetime import datetime, timedelta, date
from app.core.utils import utc_now
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case as sql_case, cast, Date as SADate

from app.core.database import get_db
from app.models.models import AgentRun, WorkflowRun

router = APIRouter(prefix="/api/observability", tags=["可观测面板"])


def _get_cutoff(days: int) -> datetime:
    """获取截止时间"""
    return utc_now() - timedelta(days=days)


# ───────────── GET /api/observability/summary ─────────────

@router.get("/summary")
def get_summary(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """返回概览指标：今日分析量（及昨日同比）、平均响应时间、LLM 成功率、降级触发次数"""
    cutoff = _get_cutoff(days)
    today = date.today()
    yesterday = today - timedelta(days=1)

    # 今日分析量（已完成的 workflow_runs）
    today_count = (
        db.query(func.count(WorkflowRun.id))
        .filter(func.date(WorkflowRun.started_at) == today)
        .scalar()
    ) or 0

    # 昨日分析量
    yesterday_count = (
        db.query(func.count(WorkflowRun.id))
        .filter(func.date(WorkflowRun.started_at) == yesterday)
        .scalar()
    ) or 0

    # 同比变化
    if yesterday_count > 0:
        today_change_pct = round((today_count - yesterday_count) / yesterday_count * 100, 1)
    else:
        today_change_pct = 100.0 if today_count > 0 else 0.0

    # 平均响应时间（agent_runs latency_ms）
    avg_latency = (
        db.query(func.avg(AgentRun.latency_ms))
        .filter(AgentRun.created_at >= cutoff, AgentRun.latency_ms.isnot(None))
        .scalar()
    )
    avg_latency_ms = round(float(avg_latency), 1) if avg_latency else 0.0

    # LLM 调用成功率
    total_runs = (
        db.query(func.count(AgentRun.id))
        .filter(AgentRun.created_at >= cutoff)
        .scalar()
    ) or 0

    success_runs = (
        db.query(func.count(AgentRun.id))
        .filter(AgentRun.created_at >= cutoff, AgentRun.status == "SUCCESS")
        .scalar()
    ) or 0

    success_rate = round(success_runs / total_runs * 100, 1) if total_runs > 0 else 0.0

    # 降级触发次数（FAILED 的 agent_runs）
    failed_runs = (
        db.query(func.count(AgentRun.id))
        .filter(AgentRun.created_at >= cutoff, AgentRun.status == "FAILED")
        .scalar()
    ) or 0

    return {
        "today_analysis_count": today_count,
        "today_change_pct": today_change_pct,
        "avg_latency_ms": avg_latency_ms,
        "llm_success_rate": success_rate,
        "total_agent_runs": total_runs,
        "degradation_count": failed_runs,
        "days": days,
    }


# ───────────── GET /api/observability/latency-trend ─────────────

@router.get("/latency-trend")
def get_latency_trend(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """返回按天聚合的平均 latency_ms 趋势数据"""
    cutoff = _get_cutoff(days)

    # 按天聚合
    results = (
        db.query(
            func.date(AgentRun.created_at).label("day"),
            func.avg(AgentRun.latency_ms).label("avg_latency"),
            func.count(AgentRun.id).label("count"),
        )
        .filter(AgentRun.created_at >= cutoff, AgentRun.latency_ms.isnot(None))
        .group_by(func.date(AgentRun.created_at))
        .order_by(func.date(AgentRun.created_at))
        .all()
    )

    # 填充无数据的天数
    trend = []
    today = date.today()
    for i in range(days, 0, -1):
        d = today - timedelta(days=i - 1)
        d_str = str(d)
        found = next((r for r in results if str(r.day) == d_str), None)
        trend.append({
            "date": d_str,
            "avg_latency_ms": round(float(found.avg_latency), 1) if found else 0,
            "count": found.count if found else 0,
        })

    return {"trend": trend, "days": days}


# ───────────── GET /api/observability/agent-latency ─────────────

@router.get("/agent-latency")
def get_agent_latency(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """返回各 agent_name 的平均 latency_ms 排行"""
    cutoff = _get_cutoff(days)

    results = (
        db.query(
            AgentRun.agent_name,
            func.avg(AgentRun.latency_ms).label("avg_latency"),
            func.count(AgentRun.id).label("count"),
        )
        .filter(AgentRun.created_at >= cutoff, AgentRun.latency_ms.isnot(None))
        .group_by(AgentRun.agent_name)
        .order_by(func.avg(AgentRun.latency_ms).desc())
        .all()
    )

    return {
        "agents": [
            {
                "agent_name": r.agent_name,
                "avg_latency_ms": round(float(r.avg_latency), 1),
                "count": r.count,
            }
            for r in results
        ],
        "days": days,
    }


# ───────────── GET /api/observability/workflow-status ─────────────

@router.get("/workflow-status")
def get_workflow_status(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """返回 workflow_runs 状态分布"""
    cutoff = _get_cutoff(days)

    results = (
        db.query(
            WorkflowRun.status,
            func.count(WorkflowRun.id).label("count"),
        )
        .filter(WorkflowRun.started_at >= cutoff)
        .group_by(WorkflowRun.status)
        .all()
    )

    total = sum(r.count for r in results) if results else 0

    return {
        "statuses": [
            {
                "status": r.status,
                "count": r.count,
                "percentage": round(r.count / total * 100, 1) if total > 0 else 0,
            }
            for r in results
        ],
        "total": total,
        "days": days,
    }
