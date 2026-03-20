"""
风险案件自动生成服务

扫描所有商家，基于业务规则自动创建/更新风险案件。
"""
import json
from datetime import datetime, date
from app.core.utils import utc_now
from sqlalchemy.orm import Session

from app.models.models import Merchant, RiskCase
from app.engine.metrics import get_all_metrics
from app.engine.cashflow import forecast_cash_gap
from app.core.config import settings


def assess_risk_level(metrics: dict, predicted_gap: float) -> str:
    """根据规则评定风险等级"""
    amplification = metrics["return_amplification"]
    anomaly = metrics["anomaly_score"]
    delay = metrics["avg_settlement_delay"]

    # High
    if (amplification >= settings.HIGH_RISK_AMPLIFICATION and predicted_gap >= settings.HIGH_RISK_GAP):
        return "high"
    if anomaly >= settings.HIGH_RISK_ANOMALY:
        return "high"

    # Medium
    if amplification >= settings.MEDIUM_RISK_AMPLIFICATION:
        return "medium"
    if delay >= settings.MEDIUM_RISK_DELAY:
        return "medium"

    return "low"


def check_triggers(metrics: dict, predicted_gap: float) -> list:
    """检查触发条件，返回命中的触发规则列表"""
    triggers = []

    if metrics["return_amplification"] >= settings.RETURN_RATE_AMPLIFICATION_THRESHOLD:
        triggers.append({
            "rule": "return_rate_amplification >= 1.6",
            "value": metrics["return_amplification"],
        })

    if predicted_gap >= settings.PREDICTED_GAP_THRESHOLD:
        triggers.append({
            "rule": "predicted_gap >= 50000",
            "value": predicted_gap,
        })

    if metrics["avg_settlement_delay"] >= settings.SETTLEMENT_DELAY_THRESHOLD:
        triggers.append({
            "rule": "avg_settlement_delay >= 3",
            "value": metrics["avg_settlement_delay"],
        })

    if metrics["anomaly_score"] >= settings.ANOMALY_SCORE_THRESHOLD:
        triggers.append({
            "rule": "anomaly_score >= 0.8",
            "value": metrics["anomaly_score"],
        })

    return triggers


def compute_risk_score(metrics: dict, predicted_gap: float) -> float:
    """计算综合风险分数 (0-100)"""
    score = 0.0

    # 退货率放大倍数贡献 (0-30)
    amp = metrics["return_amplification"]
    if amp >= 2.0:
        score += 30
    elif amp >= 1.6:
        score += 20
    elif amp >= 1.3:
        score += 10

    # 现金缺口贡献 (0-30)
    if predicted_gap >= 100000:
        score += 30
    elif predicted_gap >= 50000:
        score += 20
    elif predicted_gap >= 20000:
        score += 10

    # 回款延迟贡献 (0-20)
    delay = metrics["avg_settlement_delay"]
    if delay >= 5:
        score += 20
    elif delay >= 3:
        score += 15
    elif delay >= 2:
        score += 8

    # 异常分数贡献 (0-20)
    anomaly = metrics["anomaly_score"]
    score += anomaly * 20

    return round(min(100, score), 2)


def scan_merchant(db: Session, merchant: Merchant) -> dict | None:
    """扫描单个商家，返回案件数据 (如果触发) 或 None"""
    metrics = get_all_metrics(db, merchant.id)
    forecast = forecast_cash_gap(db, merchant.id, horizon_days=14)
    predicted_gap = forecast["predicted_gap"]

    triggers = check_triggers(metrics, predicted_gap)
    if not triggers:
        return None

    risk_level = assess_risk_level(metrics, predicted_gap)
    risk_score = compute_risk_score(metrics, predicted_gap)

    return {
        "merchant_id": merchant.id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "triggers": triggers,
        "metrics": metrics,
        "forecast": forecast,
    }


def generate_risk_cases(db: Session) -> list:
    """
    扫描所有商家并批量生成风险案件。
    同一商家同一天不重复生成，已有未关闭案件则更新。
    """
    merchants = db.query(Merchant).all()
    today_str = date.today().isoformat()
    cases_created = []

    for merchant in merchants:
        result = scan_merchant(db, merchant)
        if result is None:
            continue

        # 去重：查找该商家当天已有的未关闭案件
        existing = (
            db.query(RiskCase)
            .filter(
                RiskCase.merchant_id == merchant.id,
                RiskCase.status.in_(["NEW", "ANALYZED", "PENDING_REVIEW"]),
            )
            .first()
        )

        trigger_json = json.dumps(result["triggers"], ensure_ascii=False)

        if existing:
            # 更新已有案件
            existing.risk_score = result["risk_score"]
            existing.risk_level = result["risk_level"]
            existing.trigger_json = trigger_json
            existing.updated_at = utc_now()
            cases_created.append(existing)
        else:
            # 新建案件
            case = RiskCase(
                merchant_id=merchant.id,
                risk_score=result["risk_score"],
                risk_level=result["risk_level"],
                trigger_json=trigger_json,
                status="NEW",
            )
            db.add(case)
            cases_created.append(case)

    db.flush()
    return cases_created
