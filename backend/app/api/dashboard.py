"""看板 API 路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.models import RiskCase, Merchant, Settlement
from app.schemas.schemas import DashboardStats
from app.engine.cashflow import forecast_cash_gap

from datetime import date, timedelta

router = APIRouter()


@router.get("/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """看板顶部指标卡数据"""
    # 1. 监控商家数
    merchant_count = db.query(func.count(Merchant.id)).scalar()

    # 2. 今日新增高风险案件数
    today = date.today()
    new_high_risk_count = (
        db.query(func.count(RiskCase.id))
        .filter(
            RiskCase.risk_level == "high",
            func.date(RiskCase.created_at) == today,
        )
        .scalar()
    )

    # 3. 预计总现金缺口（所有活跃案件的预测缺口之和）
    active_cases = (
        db.query(RiskCase)
        .filter(RiskCase.status.in_(["NEW", "ANALYZED", "PENDING_REVIEW"]))
        .all()
    )
    total_gap = 0.0
    for case in active_cases:
        try:
            forecast = forecast_cash_gap(db, case.merchant_id, 14)
            total_gap += forecast.get("predicted_gap", 0)
        except Exception:
            pass

    # 4. 平均回款延迟
    cutoff = today - timedelta(days=30)
    settlements = (
        db.query(Settlement)
        .filter(
            Settlement.actual_settlement_date.isnot(None),
            Settlement.expected_settlement_date >= cutoff,
        )
        .all()
    )
    if settlements:
        total_delay = sum(
            max(0, (s.actual_settlement_date - s.expected_settlement_date).days)
            for s in settlements
        )
        avg_delay = round(total_delay / len(settlements), 2)
    else:
        avg_delay = 0.0

    return DashboardStats(
        merchant_count=merchant_count,
        new_high_risk_count=new_high_risk_count,
        total_predicted_gap=round(total_gap, 2),
        avg_settlement_delay=avg_delay,
    )