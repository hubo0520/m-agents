"""
任务生成引擎 — 根据 Recommendation + 规则引擎自动生成执行任务

统一入口函数：generate_tasks_for_case(db, case_id) -> list[dict]
"""
import json
from datetime import datetime, timedelta, date
from app.core.utils import utc_now
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import (
    RiskCase, Merchant, Recommendation, EvidenceItem,
    FinancingApplication, Claim, ManualReview,
    Order, Return, Settlement, InsurancePolicy, AuditLog,
)
from app.engine.rules import (
    check_financing_eligibility,
    check_claim_eligibility,
    check_review_trigger,
)
from app.engine.cashflow import forecast_cash_gap
from app.engine.metrics import get_all_metrics


def _build_merchant_snapshot(db: Session, merchant: Merchant) -> dict:
    """构建商家信息快照"""
    cutoff_90d = utc_now() - timedelta(days=90)

    total_sales = (
        db.query(func.sum(Order.order_amount))
        .filter(Order.merchant_id == merchant.id, Order.order_time >= cutoff_90d)
        .scalar()
    ) or 0.0

    total_returns = (
        db.query(func.sum(Return.refund_amount))
        .join(Order, Return.order_id == Order.id)
        .filter(Order.merchant_id == merchant.id, Return.return_time >= cutoff_90d)
        .scalar()
    ) or 0.0

    return {
        "merchant_id": merchant.id,
        "merchant_name": merchant.name,
        "industry": merchant.industry,
        "store_level": merchant.store_level,
        "settlement_cycle_days": merchant.settlement_cycle_days,
        "total_sales_90d": round(float(total_sales), 2),
        "total_returns_90d": round(float(total_returns), 2),
        "snapshot_time": utc_now().isoformat(),
    }


def _build_historical_settlement(db: Session, merchant_id: int) -> dict:
    """构建历史回款摘要"""
    cutoff_90d = date.today() - timedelta(days=90)

    settlements = (
        db.query(Settlement)
        .filter(
            Settlement.merchant_id == merchant_id,
            Settlement.expected_settlement_date >= cutoff_90d,
        )
        .all()
    )

    total_amount = sum(float(s.amount) for s in settlements)
    settled_count = sum(1 for s in settlements if s.status == "settled")
    delayed_count = sum(1 for s in settlements if s.status == "delayed")

    delays = []
    for s in settlements:
        if s.actual_settlement_date and s.expected_settlement_date:
            delay = (s.actual_settlement_date - s.expected_settlement_date).days
            delays.append(max(0, delay))

    avg_delay = round(sum(delays) / len(delays), 2) if delays else 0.0

    return {
        "period": "近90天",
        "total_settlement_count": len(settlements),
        "settled_count": settled_count,
        "delayed_count": delayed_count,
        "total_amount": round(total_amount, 2),
        "avg_delay_days": avg_delay,
        "delay_rate": round(delayed_count / len(settlements), 4) if settlements else 0.0,
    }


def _build_return_details(db: Session, merchant_id: int) -> dict:
    """构建退货详情摘要"""
    cutoff_14d = utc_now() - timedelta(days=14)

    returns = (
        db.query(Return, Order)
        .join(Order, Return.order_id == Order.id)
        .filter(Order.merchant_id == merchant_id, Return.return_time >= cutoff_14d)
        .all()
    )

    total_amount = sum(float(r.refund_amount) for r, _ in returns)
    total_count = len(returns)

    # 退货原因分布
    reason_dist = {}
    for r, _ in returns:
        reason = r.return_reason or "未知"
        reason_dist[reason] = reason_dist.get(reason, 0) + 1

    return {
        "period": "近14天",
        "return_count": total_count,
        "total_refund_amount": round(total_amount, 2),
        "reason_distribution": reason_dist,
    }


def _build_evidence_snapshot(db: Session, case_id: int) -> list:
    """构建证据快照"""
    evidence_items = (
        db.query(EvidenceItem)
        .filter(EvidenceItem.case_id == case_id)
        .all()
    )

    return [
        {
            "id": ev.id,
            "evidence_type": ev.evidence_type,
            "summary": ev.summary,
            "importance_score": ev.importance_score,
        }
        for ev in evidence_items
    ]


def _write_audit_log(db: Session, entity_type: str, entity_id: int, action: str, new_value: str = None):
    """写入审计日志"""
    log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        actor="task_generator",
        action=action,
        new_value=new_value,
    )
    db.add(log)


def _generate_financing_for_recommendation(
    db: Session, case: RiskCase, merchant: Merchant, rec: Recommendation, predicted_gap: float
) -> dict | None:
    """为融资类建议生成融资申请草稿"""
    # 幂等检查
    if rec.task_generated:
        return None

    eligibility = check_financing_eligibility(db, merchant.id, predicted_gap)

    if not eligibility["eligible"]:
        # 记录审计日志
        _write_audit_log(
            db, "recommendation", rec.id,
            "financing_eligibility_failed",
            json.dumps({"reasons": eligibility["rejection_reasons"]}, ensure_ascii=False),
        )
        return None

    # 构建商家快照
    snapshot = _build_merchant_snapshot(db, merchant)
    historical = _build_historical_settlement(db, merchant.id)

    # 生成还款计划（简单按月等额）
    amount = eligibility["recommended_amount"]
    months = 6  # 默认 6 个月
    monthly_payment = round(amount / months, 2)
    repayment_plan = {
        "total_amount": amount,
        "term_months": months,
        "monthly_payment": monthly_payment,
        "interest_rate": 0.05,
        "schedule": [
            {"month": i + 1, "payment": monthly_payment}
            for i in range(months)
        ],
    }

    # 创建融资申请
    application = FinancingApplication(
        merchant_id=merchant.id,
        case_id=case.id,
        recommendation_id=rec.id,
        amount_requested=amount,
        loan_purpose=f"覆盖预测现金缺口 ¥{predicted_gap:,.2f}，来源产品: {eligibility.get('product_name', '未知')}",
        repayment_plan_json=json.dumps(repayment_plan, ensure_ascii=False),
        merchant_info_snapshot_json=json.dumps(snapshot, ensure_ascii=False),
        historical_settlement_json=json.dumps(historical, ensure_ascii=False),
        approval_status="DRAFT",
    )
    db.add(application)
    db.flush()

    # 更新 Recommendation
    rec.task_generated = 1
    rec.task_type = "financing"
    rec.task_id = application.id

    # 审计日志
    _write_audit_log(
        db, "financing_application", application.id,
        "auto_generated",
        json.dumps({
            "case_id": case.id,
            "recommendation_id": rec.id,
            "amount": amount,
            "product": eligibility.get("product_name"),
        }, ensure_ascii=False),
    )

    return {
        "task_type": "financing",
        "task_id": application.id,
        "amount": amount,
        "product_name": eligibility.get("product_name"),
    }


def _generate_claim_for_recommendation(
    db: Session, case: RiskCase, merchant: Merchant, rec: Recommendation
) -> dict | None:
    """为理赔类建议生成理赔申请草稿"""
    if rec.task_generated:
        return None

    eligibility = check_claim_eligibility(db, merchant.id, case.id)

    if not eligibility["eligible"]:
        _write_audit_log(
            db, "recommendation", rec.id,
            "claim_eligibility_failed",
            json.dumps({"reasons": eligibility["rejection_reasons"]}, ensure_ascii=False),
        )
        return None

    # 构建退货详情和证据快照
    return_details = _build_return_details(db, merchant.id)
    evidence_snapshot = _build_evidence_snapshot(db, case.id)

    claim = Claim(
        merchant_id=merchant.id,
        case_id=case.id,
        recommendation_id=rec.id,
        policy_id=eligibility["policy_id"],
        claim_amount=eligibility["claimable_amount"],
        claim_reason=f"退货激增导致损失，近14天退款总额 ¥{eligibility['return_total_amount']:,.2f}",
        evidence_snapshot_json=json.dumps(evidence_snapshot, ensure_ascii=False),
        return_details_json=json.dumps(return_details, ensure_ascii=False),
        claim_status="DRAFT",
    )
    db.add(claim)
    db.flush()

    rec.task_generated = 1
    rec.task_type = "claim"
    rec.task_id = claim.id

    _write_audit_log(
        db, "claim", claim.id,
        "auto_generated",
        json.dumps({
            "case_id": case.id,
            "recommendation_id": rec.id,
            "amount": eligibility["claimable_amount"],
            "policy_id": eligibility["policy_id"],
        }, ensure_ascii=False),
    )

    return {
        "task_type": "claim",
        "task_id": claim.id,
        "amount": eligibility["claimable_amount"],
        "policy_id": eligibility["policy_id"],
    }


def _generate_review_for_recommendation(
    db: Session, case: RiskCase, merchant: Merchant, rec: Recommendation, agent_output: dict = None
) -> dict | None:
    """为复核类建议生成人工复核任务"""
    if rec.task_generated:
        return None

    trigger = check_review_trigger(db, merchant.id, case.id, agent_output)

    if not trigger["should_review"]:
        return None

    # 收集证据 ID
    evidence_items = db.query(EvidenceItem).filter(EvidenceItem.case_id == case.id).all()
    evidence_ids = [ev.id for ev in evidence_items]

    review = ManualReview(
        merchant_id=merchant.id,
        case_id=case.id,
        recommendation_id=rec.id,
        task_type=trigger["review_type"],
        review_reason=trigger["review_reason"],
        evidence_ids_json=json.dumps(evidence_ids),
        assigned_to="unassigned",
        status="PENDING",
    )
    db.add(review)
    db.flush()

    rec.task_generated = 1
    rec.task_type = "manual_review"
    rec.task_id = review.id

    _write_audit_log(
        db, "manual_review", review.id,
        "auto_generated",
        json.dumps({
            "case_id": case.id,
            "recommendation_id": rec.id,
            "review_type": trigger["review_type"],
        }, ensure_ascii=False),
    )

    return {
        "task_type": "manual_review",
        "task_id": review.id,
        "review_type": trigger["review_type"],
    }


def _generate_mandatory_review(
    db: Session, case: RiskCase, merchant: Merchant, agent_output: dict = None
) -> dict | None:
    """高风险案件强制生成复核任务（即使没有 anomaly_review 类型的建议）"""
    risk_level = case.risk_level
    manual_required = agent_output.get("manual_review_required", False) if agent_output else False

    if risk_level != "high" or not manual_required:
        return None

    # 检查是否已有复核任务
    existing = (
        db.query(ManualReview)
        .filter(ManualReview.case_id == case.id)
        .first()
    )
    if existing:
        return None

    evidence_items = db.query(EvidenceItem).filter(EvidenceItem.case_id == case.id).all()
    evidence_ids = [ev.id for ev in evidence_items]

    review = ManualReview(
        merchant_id=merchant.id,
        case_id=case.id,
        recommendation_id=None,
        task_type="high_risk_mandatory",
        review_reason=f"高风险案件（等级={risk_level}）强制复核",
        evidence_ids_json=json.dumps(evidence_ids),
        assigned_to="unassigned",
        status="PENDING",
    )
    db.add(review)
    db.flush()

    _write_audit_log(
        db, "manual_review", review.id,
        "mandatory_generated",
        json.dumps({"case_id": case.id, "risk_level": risk_level}, ensure_ascii=False),
    )

    return {
        "task_type": "manual_review",
        "task_id": review.id,
        "review_type": "high_risk_mandatory",
    }


# ─────── 映射: action_type → 任务生成函数 ───────
FINANCING_ACTIONS = {"business_loan", "repayment_acceleration", "advance_settlement"}
CLAIM_ACTIONS = {"insurance_claim", "insurance_adjust"}
REVIEW_ACTIONS = {"anomaly_review"}


def generate_tasks_for_case(db: Session, case_id: int) -> list[dict]:
    """
    统一任务生成入口。

    遍历案件所有 Recommendation，根据 action_type 调用对应规则引擎判断，
    符合条件的自动生成执行任务。

    返回已生成任务的列表。
    """
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        return []

    merchant = db.query(Merchant).filter(Merchant.id == case.merchant_id).first()
    if not merchant:
        return []

    # 获取 agent_output
    agent_output = None
    if case.agent_output_json:
        try:
            agent_output = json.loads(case.agent_output_json)
        except (json.JSONDecodeError, TypeError):
            pass

    # 获取现金缺口预测
    try:
        forecast = forecast_cash_gap(db, merchant.id, horizon_days=14)
        predicted_gap = forecast.get("predicted_gap", 0)
    except Exception:
        predicted_gap = 0

    # 获取所有建议
    recommendations = db.query(Recommendation).filter(Recommendation.case_id == case_id).all()
    generated = []

    for rec in recommendations:
        # 幂等检查
        if rec.task_generated:
            continue

        action_type = rec.action_type

        if action_type in FINANCING_ACTIONS:
            result = _generate_financing_for_recommendation(db, case, merchant, rec, predicted_gap)
            if result:
                generated.append(result)

        elif action_type in CLAIM_ACTIONS:
            result = _generate_claim_for_recommendation(db, case, merchant, rec)
            if result:
                generated.append(result)

        elif action_type in REVIEW_ACTIONS:
            result = _generate_review_for_recommendation(db, case, merchant, rec, agent_output)
            if result:
                generated.append(result)

    # 高风险强制复核
    mandatory = _generate_mandatory_review(db, case, merchant, agent_output)
    if mandatory:
        generated.append(mandatory)

    db.flush()
    return generated
