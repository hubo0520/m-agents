"""
数值分析引擎 — 所有核心指标由纯 Python 函数计算

所有函数接受 SQLAlchemy Session 和 merchant_id，返回确定性结果。
"""
from datetime import datetime, timedelta, date
from app.core.utils import utc_now
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional

from app.models.models import Order, Return, Settlement


def compute_return_rate(db: Session, merchant_id: int, days: int = 7) -> float:
    """计算指定商家近 N 天的退货率（退货订单数 / 总订单数）"""
    cutoff = utc_now() - timedelta(days=days)

    total_orders = (
        db.query(func.count(Order.id))
        .filter(Order.merchant_id == merchant_id, Order.order_time >= cutoff)
        .scalar()
    )
    if total_orders == 0:
        return 0.0

    # 统计有退货记录的订单数
    returned_orders = (
        db.query(func.count(func.distinct(Return.order_id)))
        .join(Order, Return.order_id == Order.id)
        .filter(Order.merchant_id == merchant_id, Order.order_time >= cutoff)
        .scalar()
    )

    return round(returned_orders / total_orders, 4)


def compute_baseline_return_rate(db: Session, merchant_id: int) -> float:
    """计算近 28 日的退货率作为基线"""
    return compute_return_rate(db, merchant_id, days=28)


def compute_return_amplification(db: Session, merchant_id: int) -> float:
    """计算退货率放大倍数: 7 日退货率 / 28 日基线退货率"""
    rate_7d = compute_return_rate(db, merchant_id, days=7)
    baseline = compute_baseline_return_rate(db, merchant_id)

    if baseline == 0:
        return 0.0  # 安全处理除零
    return round(rate_7d / baseline, 2)


def compute_avg_settlement_delay(db: Session, merchant_id: int) -> float:
    """计算近 30 天内已回款记录的平均延迟天数"""
    cutoff = date.today() - timedelta(days=30)

    settlements = (
        db.query(Settlement)
        .filter(
            Settlement.merchant_id == merchant_id,
            Settlement.expected_settlement_date >= cutoff,
            Settlement.actual_settlement_date.isnot(None),
        )
        .all()
    )

    if not settlements:
        return 0.0

    total_delay = 0.0
    for s in settlements:
        delay = (s.actual_settlement_date - s.expected_settlement_date).days
        total_delay += max(0, delay)

    return round(total_delay / len(settlements), 2)


def compute_refund_pressure(db: Session, merchant_id: int, days: int = 7) -> float:
    """计算指定天数内的退款总金额"""
    cutoff = utc_now() - timedelta(days=days)

    total = (
        db.query(func.sum(Return.refund_amount))
        .join(Order, Return.order_id == Order.id)
        .filter(Order.merchant_id == merchant_id, Return.return_time >= cutoff)
        .scalar()
    )

    return round(total or 0.0, 2)


def compute_anomaly_score(db: Session, merchant_id: int) -> float:
    """
    计算异常退货分数 (0-1)，基于以下信号:
    1. 同一退货原因短期高频出现
    2. 签收后极短时间内退款
    3. 退货率突变幅度
    """
    cutoff = utc_now() - timedelta(days=14)

    # 获取近 14 天退货记录
    returns_data = (
        db.query(Return, Order)
        .join(Order, Return.order_id == Order.id)
        .filter(Order.merchant_id == merchant_id, Return.return_time >= cutoff)
        .all()
    )

    if not returns_data:
        return 0.0

    scores = []

    # 信号1: 同一原因高频出现 (占比 > 50%)
    reason_counts = {}
    for ret, _ in returns_data:
        reason = ret.return_reason or "未知"
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    total_returns = len(returns_data)
    if total_returns > 0:
        max_reason_ratio = max(reason_counts.values()) / total_returns
        if max_reason_ratio > 0.5:
            scores.append(min(1.0, max_reason_ratio))
        else:
            scores.append(max_reason_ratio * 0.5)

    # 信号2: 签收后极短时间退款 (24小时内)
    quick_return_count = 0
    for ret, order in returns_data:
        if order.delivered_time and ret.return_time:
            hours_diff = (ret.return_time - order.delivered_time).total_seconds() / 3600
            if 0 < hours_diff < 24:
                quick_return_count += 1

    if total_returns > 0:
        quick_ratio = quick_return_count / total_returns
        scores.append(min(1.0, quick_ratio * 2))  # 放大信号

    # 信号3: 退货率突变 (7日 vs 28日)
    amplification = compute_return_amplification(db, merchant_id)
    if amplification >= 2.0:
        scores.append(0.8)
    elif amplification >= 1.5:
        scores.append(0.4)
    else:
        scores.append(0.1)

    # 综合分数: 加权平均
    if not scores:
        return 0.0

    weights = [0.35, 0.40, 0.25]
    weighted_sum = sum(s * w for s, w in zip(scores, weights[:len(scores)]))
    total_weight = sum(weights[:len(scores)])

    return round(min(1.0, weighted_sum / total_weight), 4)


def get_all_metrics(db: Session, merchant_id: int) -> dict:
    """获取商家所有核心指标的聚合结果"""
    return {
        "return_rate_7d": compute_return_rate(db, merchant_id, 7),
        "baseline_return_rate": compute_baseline_return_rate(db, merchant_id),
        "return_amplification": compute_return_amplification(db, merchant_id),
        "avg_settlement_delay": compute_avg_settlement_delay(db, merchant_id),
        "refund_pressure_7d": compute_refund_pressure(db, merchant_id, 7),
        "refund_pressure_14d": compute_refund_pressure(db, merchant_id, 14),
        "anomaly_score": compute_anomaly_score(db, merchant_id),
    }
