"""
规则引擎 — 融资资格判断、理赔条件匹配、复核触发条件评估

所有规则函数接受 SQLAlchemy Session，返回确定性结果。
"""
import json
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import (
    Merchant, Order, Return, Settlement,
    InsurancePolicy, FinancingProduct, RiskCase, EvidenceItem,
)
from app.engine.metrics import (
    compute_return_rate, compute_baseline_return_rate,
    compute_return_amplification, compute_avg_settlement_delay,
    get_all_metrics,
)
from app.engine.cashflow import forecast_cash_gap


def check_financing_eligibility(db: Session, merchant_id: int, predicted_gap: float) -> dict:
    """
    融资资格判断。

    检查条件:
    1. 近 90 天总销售额 > 融资产品最低销售额要求
    2. 退货率 < 融资产品最大允许退货率
    3. 回款延迟天数 < 融资产品最大允许延迟天数
    4. 店铺等级在融资产品允许等级列表中

    返回:
    {
        "eligible": True/False,
        "recommended_amount": float,  # 推荐融资金额
        "product_id": int,            # 匹配的融资产品
        "product_name": str,
        "rejection_reasons": []       # 不通过原因列表
    }
    """
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        return {"eligible": False, "rejection_reasons": ["商家不存在"], "recommended_amount": 0}

    # 获取所有 active 融资产品
    products = db.query(FinancingProduct).filter(FinancingProduct.status == "active").all()
    if not products:
        return {"eligible": False, "rejection_reasons": ["无可用融资产品"], "recommended_amount": 0}

    # 计算商家指标
    cutoff_90d = datetime.utcnow() - timedelta(days=90)
    total_sales_90d = (
        db.query(func.sum(Order.order_amount))
        .filter(Order.merchant_id == merchant_id, Order.order_time >= cutoff_90d)
        .scalar()
    ) or 0.0

    return_rate_28d = compute_baseline_return_rate(db, merchant_id)
    avg_delay = compute_avg_settlement_delay(db, merchant_id)

    # 店铺等级权重
    level_order = {"gold": 3, "silver": 2, "bronze": 1}
    merchant_level_rank = level_order.get(merchant.store_level, 0)

    # 遍历融资产品，寻找最佳匹配
    best_product = None
    best_amount = 0
    all_reasons = []

    for product in products:
        reasons = []
        rules = {}
        if product.eligibility_rule_json:
            try:
                rules = json.loads(product.eligibility_rule_json)
            except (json.JSONDecodeError, TypeError):
                rules = {}

        # 检查最低销售额（默认 10000）
        min_sales = rules.get("min_total_sales_90d", 10000)
        if total_sales_90d < min_sales:
            reasons.append(f"近90天销售额 {total_sales_90d:.0f} < 要求 {min_sales}")

        # 检查最大退货率（默认 0.30）
        max_return_rate = rules.get("max_return_rate", 0.30)
        if return_rate_28d > max_return_rate:
            reasons.append(f"退货率 {return_rate_28d:.2%} > 允许上限 {max_return_rate:.2%}")

        # 检查最大回款延迟（默认 10 天）
        max_delay = rules.get("max_settlement_delay", 10)
        if avg_delay > max_delay:
            reasons.append(f"平均回款延迟 {avg_delay:.1f}天 > 允许上限 {max_delay}天")

        # 检查店铺等级（默认 bronze 即可）
        min_level = rules.get("min_store_level", "bronze")
        min_level_rank = level_order.get(min_level, 0)
        if merchant_level_rank < min_level_rank:
            reasons.append(f"店铺等级 {merchant.store_level} < 要求 {min_level}")

        if not reasons:
            # 通过资格检查，计算推荐融资金额
            # 当 predicted_gap > 0 时，取缺口与产品最大额度的较小值
            # 当 predicted_gap = 0 时（退款压力场景），使用近14天退货总金额作为参考
            if predicted_gap > 0:
                recommended = min(predicted_gap, product.max_amount)
            else:
                # 计算近14天退货退款总额作为资金需求参考
                cutoff_14d = datetime.utcnow() - timedelta(days=14)
                refund_total = (
                    db.query(func.sum(Return.refund_amount))
                    .join(Order, Return.order_id == Order.id)
                    .filter(Order.merchant_id == merchant_id, Return.return_time >= cutoff_14d)
                    .scalar()
                ) or 0.0
                recommended = min(max(refund_total, 10000), product.max_amount)

            if recommended >= best_amount and recommended > 0:
                best_amount = recommended
                best_product = product
        else:
            all_reasons.extend(reasons)

    if best_product:
        return {
            "eligible": True,
            "recommended_amount": round(best_amount, 2),
            "product_id": best_product.id,
            "product_name": best_product.name,
            "rejection_reasons": [],
        }
    else:
        # 去重
        unique_reasons = list(set(all_reasons))
        return {
            "eligible": False,
            "recommended_amount": 0,
            "rejection_reasons": unique_reasons,
        }


def check_claim_eligibility(db: Session, merchant_id: int, case_id: int) -> dict:
    """
    理赔条件匹配。

    检查条件:
    1. 商家存在 status=active 的保险保单
    2. 退货金额未超过保单覆盖上限

    返回:
    {
        "eligible": True/False,
        "policy_id": int,
        "claimable_amount": float,    # 可理赔金额
        "return_total_amount": float,  # 退货总金额
        "rejection_reasons": []
    }
    """
    # 检查有效保单
    policies = (
        db.query(InsurancePolicy)
        .filter(InsurancePolicy.merchant_id == merchant_id, InsurancePolicy.status == "active")
        .all()
    )

    if not policies:
        return {
            "eligible": False,
            "policy_id": None,
            "claimable_amount": 0,
            "return_total_amount": 0,
            "rejection_reasons": ["无有效保险保单"],
        }

    # 计算近 14 天退货总金额
    cutoff_14d = datetime.utcnow() - timedelta(days=14)
    return_total = (
        db.query(func.sum(Return.refund_amount))
        .join(Order, Return.order_id == Order.id)
        .filter(Order.merchant_id == merchant_id, Return.return_time >= cutoff_14d)
        .scalar()
    ) or 0.0

    # 找最大覆盖的保单
    best_policy = None
    best_claimable = 0

    for policy in policies:
        claimable = min(return_total, policy.coverage_limit)
        if claimable > best_claimable:
            best_claimable = claimable
            best_policy = policy

    if best_policy:
        return {
            "eligible": True,
            "policy_id": best_policy.id,
            "claimable_amount": round(best_claimable, 2),
            "return_total_amount": round(return_total, 2),
            "rejection_reasons": [],
        }
    else:
        return {
            "eligible": False,
            "policy_id": None,
            "claimable_amount": 0,
            "return_total_amount": round(return_total, 2),
            "rejection_reasons": ["无匹配的保险保单"],
        }


def check_review_trigger(db: Session, merchant_id: int, case_id: int, agent_output: dict = None) -> dict:
    """
    复核触发条件评估。

    检查条件:
    1. 退货率放大倍数 >= 2.0 → return_fraud
    2. 案件 risk_level 为 high 且 manual_review_required=true → high_risk_mandatory

    返回:
    {
        "should_review": True/False,
        "review_type": str,
        "review_reason": str,
    }
    """
    amplification = compute_return_amplification(db, merchant_id)

    # 从案件获取 risk_level
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    risk_level = case.risk_level if case else "low"

    # 从 agent_output 获取 manual_review_required
    manual_review_required = False
    if agent_output:
        manual_review_required = agent_output.get("manual_review_required", False)

    # 条件 1: 退货率异常放大
    if amplification >= 2.0:
        return {
            "should_review": True,
            "review_type": "return_fraud",
            "review_reason": f"退货率放大倍数异常: {amplification:.2f}x（阈值 2.0x），需人工核实是否存在退货欺诈行为",
        }

    # 条件 2: 高风险强制复核
    if risk_level == "high" and manual_review_required:
        return {
            "should_review": True,
            "review_type": "high_risk_mandatory",
            "review_reason": f"高风险案件（等级={risk_level}）且 Agent 判定需人工复核",
        }

    # 条件 3: 中等异常也可触发（放大 >= 1.5 且高风险）
    if amplification >= 1.5 and risk_level == "high":
        return {
            "should_review": True,
            "review_type": "anomaly_review",
            "review_reason": f"退货率放大倍数 {amplification:.2f}x 且风险等级为 high，建议人工复核",
        }

    return {
        "should_review": False,
        "review_type": None,
        "review_reason": None,
    }


# ═══════════════════════════════════════════════════════════════
# V3: 规则引擎降级辅助函数
# ═══════════════════════════════════════════════════════════════

def evaluate_risk(db: Session, merchant_id: int) -> dict:
    """
    规则引擎风险评估（L2 降级时使用）。

    基于指标计算风险等级和摘要。
    """
    from app.engine.metrics import get_all_metrics
    from app.engine.cashflow import forecast_cash_gap

    try:
        metrics = get_all_metrics(db, merchant_id)
    except Exception:
        metrics = {}

    try:
        forecast = forecast_cash_gap(db, merchant_id, 14)
        predicted_gap = forecast.get("predicted_gap", 0)
    except Exception:
        predicted_gap = 0

    amp = metrics.get("return_amplification", 0)
    return_rate = metrics.get("return_rate_7d", 0)
    delay = metrics.get("avg_settlement_delay", 0)

    # 综合评分
    score = 0
    factors = {}

    if amp >= 2.0:
        score += 30
        factors["return_amplification"] = f"退货放大{amp:.1f}x，严重异常"
    elif amp >= 1.5:
        score += 20
        factors["return_amplification"] = f"退货放大{amp:.1f}x，轻度异常"

    if predicted_gap >= 100000:
        score += 30
        factors["cash_gap"] = f"预测缺口¥{predicted_gap:,.0f}，较大"
    elif predicted_gap >= 50000:
        score += 20
        factors["cash_gap"] = f"预测缺口¥{predicted_gap:,.0f}，中等"

    if delay >= 5:
        score += 20
        factors["settlement_delay"] = f"平均延迟{delay:.1f}天，严重"
    elif delay >= 3:
        score += 15
        factors["settlement_delay"] = f"平均延迟{delay:.1f}天，异常"

    # 确定风险等级
    if score >= 60:
        risk_level = "high"
    elif score >= 30:
        risk_level = "medium"
    else:
        risk_level = "low"

    summary_parts = [f"风险分数 {score} 分"]
    for k, v in factors.items():
        summary_parts.append(v)

    return {
        "risk_level": risk_level,
        "risk_score": score,
        "factors": factors,
        "summary": "；".join(summary_parts),
    }


def generate_rule_recommendations(db: Session, merchant_id: int) -> list:
    """
    规则引擎生成建议（L2 降级时使用）。

    基于预定义规则为商家生成保障建议。
    """
    from app.engine.cashflow import forecast_cash_gap

    try:
        forecast = forecast_cash_gap(db, merchant_id, 14)
        predicted_gap = forecast.get("predicted_gap", 0)
    except Exception:
        predicted_gap = 0

    recommendations = []

    # 规则 1: 现金缺口较大 → 建议回款加速
    if predicted_gap >= 30000:
        recommendations.append({
            "action_type": "advance_settlement",
            "title": "建议回款加速",
            "reason": f"预测14日现金缺口 ¥{predicted_gap:,.0f}，建议申请回款加速缓解现金流压力",
            "amount": round(predicted_gap * 0.7, 2),
            "priority": "high",
            "confidence": 0.6,
            "requires_manual_review": True,
            "evidence_ids": [],
        })

    # 规则 2: 缺口极大 → 经营贷
    if predicted_gap >= 80000:
        recommendations.append({
            "action_type": "business_loan",
            "title": "建议经营贷",
            "reason": f"预测14日现金缺口 ¥{predicted_gap:,.0f}，超过回款加速覆盖范围，建议申请经营贷",
            "amount": round(predicted_gap * 0.5, 2),
            "priority": "high",
            "confidence": 0.5,
            "requires_manual_review": True,
            "evidence_ids": [],
        })

    # 规则 3: 默认总有一个人工复核建议
    if not recommendations:
        recommendations.append({
            "action_type": "anomaly_review",
            "title": "建议人工复核",
            "reason": "规则引擎降级模式，建议人工复核商家经营状况",
            "priority": "medium",
            "confidence": 0.4,
            "requires_manual_review": True,
            "evidence_ids": [],
        })

    return recommendations
