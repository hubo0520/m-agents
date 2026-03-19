"""
分析 Agent（Mock 实现）

基于规则生成案件摘要 JSON。
"""
from typing import List

from app.agents.schemas import RootCause


def generate_summary(metrics: dict, evidence: List[dict]) -> dict:
    """
    基于指标和证据生成案件摘要。
    返回 risk_level、case_summary、root_causes、manual_review_required
    """
    root_causes = []
    manual_review = False

    # 构建 evidence_id 映射
    return_ev_ids = [e["evidence_id"] for e in evidence if e["type"] == "return"]
    settlement_ev_ids = [e["evidence_id"] for e in evidence if e["type"] == "settlement"]
    rule_ev_ids = [e["evidence_id"] for e in evidence if e["type"] == "rule_hit"]

    # 根因1: 退货率异常上升
    amp = metrics.get("return_amplification", 0)
    rate_7d = metrics.get("return_rate_7d", 0)
    baseline = metrics.get("baseline_return_rate", 0)
    if amp >= 1.3:
        root_causes.append(RootCause(
            label="退货率异常上升",
            explanation=f"近7日退货率{rate_7d*100:.1f}%，高于28日基线{baseline*100:.1f}%，放大倍数{amp:.1f}x。",
            confidence=min(0.95, 0.5 + amp * 0.2),
            evidence_ids=return_ev_ids[:2] + rule_ev_ids[:1],
        ))

    # 根因2: 回款延迟
    delay = metrics.get("avg_settlement_delay", 0)
    if delay >= 2:
        root_causes.append(RootCause(
            label="回款延迟扩大",
            explanation=f"近30天平均回款延迟{delay:.1f}天，影响现金流。",
            confidence=min(0.9, 0.4 + delay * 0.15),
            evidence_ids=settlement_ev_ids[:2] + rule_ev_ids[:1],
        ))

    # 根因3: 异常退货模式
    anomaly = metrics.get("anomaly_score", 0)
    if anomaly >= 0.5:
        manual_review = True
        root_causes.append(RootCause(
            label="疑似异常退货模式",
            explanation=f"异常退货分数{anomaly:.2f}，存在同一原因高频退货或签收后极短时间退款。",
            confidence=anomaly,
            evidence_ids=return_ev_ids[:3],
        ))

    # 限制最多 3 条
    root_causes = root_causes[:3]

    # 生成摘要文本
    summary_parts = []
    if amp >= 1.3:
        summary_parts.append(f"近7日退货率显著高于近28日基线（放大{amp:.1f}倍）")
    if delay >= 2:
        summary_parts.append(f"回款延迟扩大至{delay:.1f}天")
    if anomaly >= 0.5:
        summary_parts.append("存在疑似异常退货模式")

    refund_7d = metrics.get("refund_pressure_7d", 0)
    if refund_7d > 0:
        summary_parts.append(f"7日退款压力¥{refund_7d:,.0f}")

    case_summary = "该商家" + "，".join(summary_parts) + "。" if summary_parts else "暂无显著风险信号。"

    # 判断风险等级
    risk_level = "low"
    if (amp >= 1.6 and metrics.get("predicted_gap", 0) >= 50000) or anomaly >= 0.8:
        risk_level = "high"
    elif amp >= 1.3 or delay >= 2:
        risk_level = "medium"

    return {
        "risk_level": risk_level,
        "case_summary": case_summary,
        "root_causes": [rc.model_dump() for rc in root_causes],
        "manual_review_required": manual_review,
    }


# ═══════════════════════════════════════════════════════════════
# V3 适配器：将 generate_summary 输出适配为 DiagnosisOutput
# ═══════════════════════════════════════════════════════════════

from app.agents.schemas import AgentInput, DiagnosisOutput, DiagnosisRootCause


def run_diagnosis(agent_input: AgentInput, metrics: dict, evidence: list, on_llm_event=None) -> DiagnosisOutput:
    """V3 适配器：将现有分析逻辑包装为 DiagnosisOutput，支持 LLM / 规则引擎双路径"""
    from app.core.llm_client import is_llm_enabled

    if is_llm_enabled():
        return _run_diagnosis_llm(agent_input, metrics, evidence, on_llm_event=on_llm_event)

    # 回退到规则引擎
    result = generate_summary(metrics, evidence)

    root_causes = []
    for rc in result.get("root_causes", []):
        root_causes.append(DiagnosisRootCause(
            label=rc["label"],
            explanation=rc["explanation"],
            confidence=rc["confidence"],
            evidence_ids=rc.get("evidence_ids", []),
            key_factors={},
        ))

    return DiagnosisOutput(
        root_causes=root_causes,
        business_summary=result.get("case_summary", ""),
        key_factors={
            "return_amplification": metrics.get("return_amplification", 0),
            "predicted_gap": metrics.get("predicted_gap", 0),
            "anomaly_score": metrics.get("anomaly_score", 0),
        },
        risk_level=result.get("risk_level", "medium"),
        manual_review_required=result.get("manual_review_required", False),
    )


# ═══════════════════════════════════════════════════════════════
# LLM 路径：通过 LLM 生成诊断结果
# ═══════════════════════════════════════════════════════════════

import json
import logging

logger = logging.getLogger(__name__)


def _run_diagnosis_llm(agent_input: AgentInput, metrics: dict, evidence: list, on_llm_event=None) -> DiagnosisOutput:
    """使用 LLM 生成诊断结果（OPENAI_BASE_URL 在 llm_client 中生效）"""
    from app.core.llm_client import structured_output, LlmEvent

    logger.info("案件 %s 使用 LLM 路径生成诊断结果", agent_input.case_id)

    system_prompt = """你是一个电商平台风险分析专家 Agent。
你的任务是根据商家的指标数据和证据，生成一份根因分析诊断报告。

分析要点：
1. 识别退货率异常、回款延迟、异常退货模式等风险信号
2. 给出根因标签、解释和置信度
3. 生成面向业务人员的可读摘要
4. 判断风险等级（high/medium/low）
5. 判断是否需要人工复核

请严格按照输出 Schema 返回结构化 JSON。"""

    user_prompt = f"""## 案件信息
- 案件编号: {agent_input.case_id}
- 商家ID: {agent_input.merchant_id}

## 商家指标
{json.dumps(metrics, ensure_ascii=False, indent=2)}

## 证据列表
{json.dumps(evidence, ensure_ascii=False, indent=2)}

请基于以上信息生成诊断分析。"""

    try:
        # 发送 llm_input 事件
        if on_llm_event:
            on_llm_event(LlmEvent(
                event_type="llm_input",
                agent_name="diagnosis_agent",
                step="diagnose_case",
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
            response_model=DiagnosisOutput,
        )

        _elapsed = int((_time.time() - _t0) * 1000)
        # 发送 llm_done 事件
        if on_llm_event:
            on_llm_event(LlmEvent(
                event_type="llm_done",
                agent_name="diagnosis_agent",
                step="diagnose_case",
                content=result.business_summary[:500] if result.business_summary else "",
                elapsed_ms=_elapsed,
            ))

        logger.info("案件 %s LLM 诊断完成 | risk_level=%s", agent_input.case_id, result.risk_level)
        return result
    except Exception as e:
        logger.error("案件 %s LLM 诊断失败，回退规则引擎: %s", agent_input.case_id, e)
        # LLM 失败时优雅回退到规则引擎
        result = generate_summary(metrics, evidence)
        root_causes = []
        for rc in result.get("root_causes", []):
            root_causes.append(DiagnosisRootCause(
                label=rc["label"],
                explanation=rc["explanation"],
                confidence=rc["confidence"],
                evidence_ids=rc.get("evidence_ids", []),
                key_factors={},
            ))
        return DiagnosisOutput(
            root_causes=root_causes,
            business_summary=result.get("case_summary", ""),
            key_factors={
                "return_amplification": metrics.get("return_amplification", 0),
                "predicted_gap": metrics.get("predicted_gap", 0),
                "anomaly_score": metrics.get("anomaly_score", 0),
            },
            risk_level=result.get("risk_level", "medium"),
            manual_review_required=result.get("manual_review_required", False),
        )