"""
推荐 Agent（Mock 实现）

根据案件指标生成动作建议。
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import List

from app.agents.schemas import ActionRecommendation
from app.models.models import Merchant
from app.core.config import settings


def generate_recommendations(
    db: Session,
    merchant: Merchant,
    metrics: dict,
    predicted_gap: float,
    evidence: List[dict],
) -> List[dict]:
    """根据案件情况输出动作建议"""
    recommendations = []

    # 构建 evidence_id 映射
    return_ev_ids = [e["evidence_id"] for e in evidence if e["type"] == "return"]
    settlement_ev_ids = [e["evidence_id"] for e in evidence if e["type"] == "settlement"]
    rule_ev_ids = [e["evidence_id"] for e in evidence if e["type"] == "rule_hit"]

    # 1. 回款加速建议
    delay = metrics.get("avg_settlement_delay", 0)
    refund_pressure = metrics.get("refund_pressure_7d", 0)
    if delay >= 2 or (predicted_gap > 0 and delay >= 1):
        gap_desc = f"预计14日内出现¥{predicted_gap:,.0f}缺口，" if predicted_gap > 0 else ""
        recommendations.append(ActionRecommendation(
            action_type="advance_settlement",
            title="建议优先发起回款加速",
            why=f"{gap_desc}商家历史回款延迟{delay:.1f}天，7日退款压力¥{refund_pressure:,.0f}。",
            expected_benefit="缓解短期流动性压力，预计可覆盖部分资金缺口",
            confidence=min(0.9, 0.5 + delay * 0.1),
            requires_manual_review=True,
            evidence_ids=settlement_ev_ids[:2] + rule_ev_ids[:1],
        ))

    # 2. 经营贷建议 — 需要资格检查
    operation_days = (datetime.utcnow() - merchant.created_at).days if merchant.created_at else 0
    anomaly = metrics.get("anomaly_score", 0)

    can_loan = (
        operation_days >= settings.MIN_OPERATION_DAYS
        and merchant.store_level in ("gold", "silver")
        and anomaly < 0.5  # 无高等级欺诈标记
        and (predicted_gap >= 5000 or refund_pressure >= 10000)  # V2: 也考虑退款压力
    )

    if can_loan:
        loan_amount = max(predicted_gap, refund_pressure)
        recommendations.append(ActionRecommendation(
            action_type="business_loan",
            title="建议生成经营贷申请草稿",
            why=f"商家经营{operation_days}天，店铺等级{merchant.store_level}，预测缺口¥{predicted_gap:,.0f}，7日退款压力¥{refund_pressure:,.0f}。",
            expected_benefit="补充中期现金流，降低经营中断风险",
            confidence=0.7,
            requires_manual_review=True,  # 融资类强制人工复核
            evidence_ids=rule_ev_ids[:1] + settlement_ev_ids[:1],
        ))

    # 3. 运费险策略调整建议
    amp = metrics.get("return_amplification", 0)
    rate_7d = metrics.get("return_rate_7d", 0)
    if amp >= 1.3 and rate_7d >= 0.15:
        recommendations.append(ActionRecommendation(
            action_type="insurance_adjust",
            title="建议对高退货SKU调整运费险策略",
            why=f"退货率放大{amp:.1f}倍，7日退货率{rate_7d*100:.1f}%，运费险赔付可能增加。",
            expected_benefit="降低运费险赔付压力，优化保费成本",
            confidence=0.75,
            requires_manual_review=False,
            evidence_ids=return_ev_ids[:2],
        ))

    # 4. 异常退货人工复核
    if anomaly >= 0.3:  # V2: 降低触发阈值以覆盖更多异常场景
        recommendations.append(ActionRecommendation(
            action_type="anomaly_review",
            title="建议将疑似异常退货转人工复核",
            why=f"异常退货分数{anomaly:.2f}，存在同一原因短期高频退货模式。",
            expected_benefit="识别潜在欺诈行为，保护平台资金安全",
            confidence=anomaly,
            requires_manual_review=True,  # 反欺诈类强制人工复核
            evidence_ids=return_ev_ids[:3],
        ))

    return [r.model_dump() for r in recommendations]


# ═══════════════════════════════════════════════════════════════
# V3 适配器：将 generate_recommendations 输出适配为 RecommendationOutput
# ═══════════════════════════════════════════════════════════════

from app.agents.schemas import (
    AgentInput, RecommendationOutput, V3ActionRecommendation, ExpectedBenefit,
)


def run_recommendations(
    agent_input: AgentInput,
    db: Session,
    merchant: Merchant,
    metrics: dict,
    predicted_gap: float,
    evidence: list,
    on_llm_event=None,
) -> RecommendationOutput:
    """V3 适配器：将现有推荐逻辑包装为 RecommendationOutput，支持 LLM / 规则引擎双路径"""
    from app.core.llm_client import is_llm_enabled

    if is_llm_enabled():
        return _run_recommendations_llm(
            agent_input, db, merchant, metrics, predicted_gap, evidence,
            on_llm_event=on_llm_event,
        )

    # ── 规则引擎路径（原有逻辑） ──
    raw_recs = generate_recommendations(db, merchant, metrics, predicted_gap, evidence)

    v3_recs = []
    for rec in raw_recs:
        v3_recs.append(V3ActionRecommendation(
            action_type=rec["action_type"],
            title=rec["title"],
            why=rec["why"],
            expected_benefit=ExpectedBenefit(
                description=rec.get("expected_benefit", ""),
                cash_relief=predicted_gap if rec["action_type"] in ("advance_settlement", "business_loan") else None,
                time_horizon_days=7 if rec["action_type"] == "advance_settlement" else None,
            ),
            confidence=rec.get("confidence", 0),
            requires_manual_review=rec.get("requires_manual_review", True),
            evidence_ids=rec.get("evidence_ids", []),
        ))

    # 判断风险等级
    risk_level = "low"
    amp = metrics.get("return_amplification", 0)
    anomaly = metrics.get("anomaly_score", 0)
    if (amp >= 1.6 and predicted_gap >= 50000) or anomaly >= 0.8:
        risk_level = "high"
    elif amp >= 1.3 or metrics.get("avg_settlement_delay", 0) >= 2:
        risk_level = "medium"

    return RecommendationOutput(
        risk_level=risk_level,
        recommendations=v3_recs,
    )


# ═══════════════════════════════════════════════════════════════
# LLM 路径：通过 LLM 生成动作建议
# ═══════════════════════════════════════════════════════════════

import json
import logging

logger = logging.getLogger(__name__)


def _run_recommendations_llm(
    agent_input: AgentInput,
    db: Session,
    merchant: Merchant,
    metrics: dict,
    predicted_gap: float,
    evidence: list,
    on_llm_event=None,
) -> RecommendationOutput:
    """使用 LLM 生成动作建议（OPENAI_BASE_URL 在 llm_client 中生效）"""
    from app.core.llm_client import structured_output, LlmEvent

    logger.info("案件 %s 使用 LLM 路径生成动作建议", agent_input.case_id)

    # 构建商家画像摘要
    merchant_profile = {
        "merchant_id": merchant.id,
        "store_name": getattr(merchant, "store_name", "未知"),
        "store_level": getattr(merchant, "store_level", "未知"),
        "operation_days": (
            (__import__("datetime").datetime.utcnow() - merchant.created_at).days
            if merchant.created_at else 0
        ),
    }

    system_prompt = """你是一个电商平台风险运营建议 Agent。
你的任务是根据商家画像、经营指标、现金流预测和证据，生成精准的保障动作建议。

可用的动作类型 (action_type):
- advance_settlement: 回款加速 — 缩短回款周期缓解短期流动性
- business_loan: 经营贷 — 通过融资补充中期现金流
- insurance_adjust: 运费险策略调整 — 降低运费险赔付压力
- anomaly_review: 异常退货人工复核 — 识别疑似欺诈行为

生成建议时请注意：
1. 每条建议的 why 字段要具体、有数据支撑，不要泛泛而谈
2. confidence 在 0~1 之间，依据证据充分度和指标严重度
3. 融资类 (business_loan) 和反欺诈类 (anomaly_review) 必须设置 requires_manual_review=true
4. 每条建议必须绑定至少 1 个 evidence_id
5. risk_level 根据整体风险判断：high/medium/low
6. expected_benefit 中 cash_relief 只在 advance_settlement 和 business_loan 时填写

请严格按照输出 Schema 返回结构化 JSON。"""

    # 提取 evidence_ids 以供 LLM 引用
    evidence_summary = []
    for e in evidence:
        evidence_summary.append({
            "evidence_id": e.get("evidence_id", ""),
            "type": e.get("type", ""),
            "summary": e.get("summary", e.get("description", "")),
        })

    user_prompt = f"""## 案件信息
- 案件编号: {agent_input.case_id}
- 商家ID: {agent_input.merchant_id}

## 商家画像
{json.dumps(merchant_profile, ensure_ascii=False, indent=2)}

## 经营指标
{json.dumps(metrics, ensure_ascii=False, indent=2)}

## 现金流预测
- 预测缺口金额: ¥{predicted_gap:,.0f}

## 证据列表 (可引用的 evidence_id)
{json.dumps(evidence_summary, ensure_ascii=False, indent=2)}

请基于以上信息生成动作建议列表。"""

    try:
        # 发送 llm_input 事件
        if on_llm_event:
            on_llm_event(LlmEvent(
                event_type="llm_input",
                agent_name="recommendation_agent",
                step="generate_recommendations",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            ))

        import time as _time
        _t0 = _time.time()

        result = structured_output(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_model=RecommendationOutput,
        )

        _elapsed = int((_time.time() - _t0) * 1000)
        # 发送 llm_done 事件
        if on_llm_event:
            rec_summary = "; ".join(r.title for r in result.recommendations)[:500]
            on_llm_event(LlmEvent(
                event_type="llm_done",
                agent_name="recommendation_agent",
                step="generate_recommendations",
                content=rec_summary,
                elapsed_ms=_elapsed,
            ))

        # 后处理：强制校验安全约束
        for rec in result.recommendations:
            if rec.action_type in ("business_loan", "anomaly_review", "fraud_review"):
                rec.requires_manual_review = True

        logger.info(
            "案件 %s LLM 建议生成完成 | risk_level=%s | 建议数=%d",
            agent_input.case_id, result.risk_level, len(result.recommendations),
        )
        return result
    except Exception as e:
        logger.error("案件 %s LLM 建议生成失败，回退规则引擎: %s", agent_input.case_id, e)
        # LLM 失败时优雅回退到规则引擎
        raw_recs = generate_recommendations(db, merchant, metrics, predicted_gap, evidence)
        v3_recs = []
        for rec in raw_recs:
            v3_recs.append(V3ActionRecommendation(
                action_type=rec["action_type"],
                title=rec["title"],
                why=rec["why"],
                expected_benefit=ExpectedBenefit(
                    description=rec.get("expected_benefit", ""),
                    cash_relief=predicted_gap if rec["action_type"] in ("advance_settlement", "business_loan") else None,
                    time_horizon_days=7 if rec["action_type"] == "advance_settlement" else None,
                ),
                confidence=rec.get("confidence", 0),
                requires_manual_review=rec.get("requires_manual_review", True),
                evidence_ids=rec.get("evidence_ids", []),
            ))

        risk_level = "low"
        amp = metrics.get("return_amplification", 0)
        anomaly = metrics.get("anomaly_score", 0)
        if (amp >= 1.6 and predicted_gap >= 50000) or anomaly >= 0.8:
            risk_level = "high"
        elif amp >= 1.3 or metrics.get("avg_settlement_delay", 0) >= 2:
            risk_level = "medium"

        return RecommendationOutput(
            risk_level=risk_level,
            recommendations=v3_recs,
        )