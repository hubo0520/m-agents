"""
14 日现金缺口预测

使用滚动均值 + 周几季节性系数 + 已知应收/应付计划
不做 ML 训练，纯 Python 实现
"""
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
import math

from app.models.models import Order, Return, Settlement


def _get_daily_historical_data(
    db: Session, merchant_id: int, lookback_days: int = 30
) -> dict:
    """获取近 N 天的每日 inflow/outflow 历史数据"""
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    today = date.today()

    # 每日订单金额 (inflow)
    daily_orders = (
        db.query(
            func.date(Order.order_time).label("day"),
            func.sum(Order.order_amount).label("total"),
        )
        .filter(Order.merchant_id == merchant_id, Order.order_time >= cutoff)
        .group_by(func.date(Order.order_time))
        .all()
    )

    # 每日退款金额 (outflow)
    daily_refunds = (
        db.query(
            func.date(Return.return_time).label("day"),
            func.sum(Return.refund_amount).label("total"),
        )
        .join(Order, Return.order_id == Order.id)
        .filter(Order.merchant_id == merchant_id, Return.return_time >= cutoff)
        .group_by(func.date(Return.return_time))
        .all()
    )

    # 转为 dict
    inflow_map = {}
    for row in daily_orders:
        day_str = str(row.day) if row.day else None
        if day_str:
            inflow_map[day_str] = float(row.total or 0)

    outflow_map = {}
    for row in daily_refunds:
        day_str = str(row.day) if row.day else None
        if day_str:
            outflow_map[day_str] = float(row.total or 0)

    return {"inflow": inflow_map, "outflow": outflow_map}


def _compute_weekday_coefficients(historical: dict) -> dict:
    """计算周几季节性系数 (0=周一 ~ 6=周日)"""
    weekday_inflows = {i: [] for i in range(7)}
    weekday_outflows = {i: [] for i in range(7)}

    for day_str, val in historical["inflow"].items():
        try:
            d = date.fromisoformat(day_str)
            weekday_inflows[d.weekday()].append(val)
        except (ValueError, TypeError):
            pass

    for day_str, val in historical["outflow"].items():
        try:
            d = date.fromisoformat(day_str)
            weekday_outflows[d.weekday()].append(val)
        except (ValueError, TypeError):
            pass

    # 总平均
    all_inflows = [v for vals in weekday_inflows.values() for v in vals]
    all_outflows = [v for vals in weekday_outflows.values() for v in vals]
    avg_inflow = sum(all_inflows) / len(all_inflows) if all_inflows else 1.0
    avg_outflow = sum(all_outflows) / len(all_outflows) if all_outflows else 1.0

    # 周几系数 = 该周几的均值 / 总均值
    inflow_coeff = {}
    outflow_coeff = {}
    for wd in range(7):
        if weekday_inflows[wd]:
            inflow_coeff[wd] = (sum(weekday_inflows[wd]) / len(weekday_inflows[wd])) / avg_inflow
        else:
            inflow_coeff[wd] = 1.0

        if weekday_outflows[wd]:
            outflow_coeff[wd] = (sum(weekday_outflows[wd]) / len(weekday_outflows[wd])) / avg_outflow
        else:
            outflow_coeff[wd] = 1.0

    return {
        "inflow_coeff": inflow_coeff,
        "outflow_coeff": outflow_coeff,
        "avg_inflow": avg_inflow,
        "avg_outflow": avg_outflow,
    }


def _get_scheduled_settlements(
    db: Session, merchant_id: int, horizon_days: int = 14
) -> dict:
    """获取已知的应收/应付计划（待结算的回款）"""
    today = date.today()
    end_date = today + timedelta(days=horizon_days)

    # 查找预计在未来 N 天到账但还未结算的回款
    pending = (
        db.query(Settlement)
        .filter(
            Settlement.merchant_id == merchant_id,
            Settlement.expected_settlement_date >= today,
            Settlement.expected_settlement_date <= end_date,
            Settlement.actual_settlement_date.is_(None),
        )
        .all()
    )

    scheduled = {}
    for s in pending:
        day_str = str(s.expected_settlement_date)
        scheduled[day_str] = scheduled.get(day_str, 0) + float(s.amount)

    return scheduled


def _compute_confidence(historical: dict) -> float:
    """基于历史数据波动性计算置信度"""
    all_inflows = list(historical["inflow"].values())
    all_outflows = list(historical["outflow"].values())

    if len(all_inflows) < 7:
        return 0.3  # 数据不足，低置信度

    # 计算变异系数 (CV = std / mean)
    mean_inflow = sum(all_inflows) / len(all_inflows) if all_inflows else 1
    if mean_inflow == 0:
        return 0.3

    variance = sum((x - mean_inflow) ** 2 for x in all_inflows) / len(all_inflows)
    std_dev = math.sqrt(variance)
    cv = std_dev / mean_inflow

    # CV 越小 → 置信度越高
    if cv < 0.2:
        return 0.85
    elif cv < 0.4:
        return 0.7
    elif cv < 0.6:
        return 0.55
    elif cv < 0.8:
        return 0.4
    else:
        return 0.3


def forecast_cash_gap(
    db: Session, merchant_id: int, horizon_days: int = 14
) -> dict:
    """
    14 日现金缺口预测

    返回:
    {
        "daily_forecast": [
            {"date": "2026-03-18", "inflow": 1200, "outflow": 800, "netflow": 400},
            ...
        ],
        "predicted_gap": 86000,         # 累计缺口（正数=缺口，负数=盈余）
        "lowest_cash_day": "2026-03-24", # 缺口最大的日期
        "confidence": 0.78,
    }
    """
    today = date.today()

    # 1. 获取历史数据
    historical = _get_daily_historical_data(db, merchant_id, lookback_days=30)

    # 2. 计算周几系数
    coefficients = _compute_weekday_coefficients(historical)

    # 3. 获取已知的应收计划
    scheduled = _get_scheduled_settlements(db, merchant_id, horizon_days)

    # 4. 预测每日现金流
    daily_forecast = []
    cumulative_netflow = 0
    lowest_netflow = float("inf")
    lowest_day = None

    for day_offset in range(1, horizon_days + 1):
        forecast_date = today + timedelta(days=day_offset)
        weekday = forecast_date.weekday()

        # 预测 inflow = 平均日收入 × 周几系数 + 当日已知回款
        predicted_inflow = (
            coefficients["avg_inflow"] * coefficients["inflow_coeff"].get(weekday, 1.0)
        )
        # 加上已知的待回款
        day_str = str(forecast_date)
        if day_str in scheduled:
            predicted_inflow += scheduled[day_str]

        # 预测 outflow = 平均日支出 × 周几系数
        predicted_outflow = (
            coefficients["avg_outflow"] * coefficients["outflow_coeff"].get(weekday, 1.0)
        )

        netflow = round(predicted_inflow - predicted_outflow, 2)
        cumulative_netflow += netflow

        daily_forecast.append({
            "date": day_str,
            "inflow": round(predicted_inflow, 2),
            "outflow": round(predicted_outflow, 2),
            "netflow": netflow,
        })

        if cumulative_netflow < lowest_netflow:
            lowest_netflow = cumulative_netflow
            lowest_day = day_str

    # 5. 缺口 = 最大负值的绝对值（如果是正的说明没缺口）
    predicted_gap = round(max(0, -lowest_netflow), 2)

    # 6. 计算置信度
    confidence = _compute_confidence(historical)

    return {
        "daily_forecast": daily_forecast,
        "predicted_gap": predicted_gap,
        "lowest_cash_day": lowest_day,
        "confidence": confidence,
    }
