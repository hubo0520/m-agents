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


def run_diagnosis(agent_input: AgentInput, metrics: dict, evidence: list, on_llm_event=None, analysis_context: str = "") -> DiagnosisOutput:
    """V3 适配器：将现有分析逻辑包装为 DiagnosisOutput，支持 LLM / 规则引擎双路径"""
    from app.core.llm_client import is_llm_enabled

    if is_llm_enabled():
        return _run_diagnosis_llm(agent_input, metrics, evidence, on_llm_event=on_llm_event, analysis_context=analysis_context)

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
from loguru import logger


DEFAULT_DIAGNOSIS_PROMPT = """你是一个电商平台资深风控分析专家 Agent，擅长从商家经营指标和证据数据中识别风险根因。

## 分析框架（请严格按以下 5 步进行推理）

**第 1 步 — 识别异常指标**：逐一检查 return_amplification、anomaly_score、avg_settlement_delay、predicted_gap、refund_pressure_7d，标注哪些指标偏离正常范围。

**第 2 步 — 关联证据链**：将异常指标与证据列表中的具体 evidence_id 对应。例如：退货放大率高 → 对应 return 类型证据；回款延迟 → 对应 settlement 类型证据。

**第 3 步 — 推断根因**：基于异常指标和关联证据，推断 1~3 个根因（root_causes）。每个根因须包含：label（中文标签）、explanation（具体数据支撑的解释）、confidence（置信度 0~1）、evidence_ids（引用的证据 ID）。

**第 4 步 — 判定风险等级**：
- **high**: anomaly_score ≥ 0.7 或 predicted_gap ≥ 100000 或 (return_amplification ≥ 1.6 且 predicted_gap ≥ 50000)
- **medium**: anomaly_score ≥ 0.3 或 return_amplification ≥ 1.3 或 avg_settlement_delay ≥ 2
- **low**: 不满足以上条件

**第 5 步 — 生成业务摘要**：用 1~2 句话概括风险全貌，面向非技术业务人员可读。

## Few-Shot 示例

**输入**:
- return_amplification: 1.8, anomaly_score: 0.35, predicted_gap: 75000, avg_settlement_delay: 3.2
- 证据: EV-101(退货,退款¥5200), EV-102(退货,退款¥3800), EV-103(回款延迟3天)

**期望输出**:
```json
{
  "root_causes": [
    {"label": "退货率异常上升", "explanation": "近7日退货放大1.8倍，EV-101和EV-102显示集中退货退款合计¥9000", "confidence": 0.82, "evidence_ids": ["EV-101", "EV-102"]},
    {"label": "回款延迟扩大", "explanation": "平均回款延迟3.2天，EV-103显示典型延迟案例", "confidence": 0.75, "evidence_ids": ["EV-103"]}
  ],
  "business_summary": "该商家近7日退货率显著放大1.8倍，同时回款延迟扩大至3.2天，预计14日内现金缺口¥75,000，需关注流动性风险。",
  "risk_level": "high",
  "manual_review_required": false
}
```

## 反面约束（严格遵守）
- ❌ 不要编造不存在的 evidence_id，只能引用输入中实际出现的证据 ID
- ❌ 不要将正常的季节性波动（如节日促销后退货率小幅上升）误判为风险信号
- ❌ 不要在 business_summary 中使用技术术语（如 anomaly_score），应转化为业务语言
- ❌ confidence 不要随意设置，必须基于证据充分度和指标偏离程度
- ❌ **label 必须使用中文**（如"退货率异常上升"、"回款延迟扩大"），严禁使用英文标签（如 operational_slippage、settlement_latency）
- ❌ **explanation 必须使用中文**，不要混入英文术语

请严格按照输出 Schema 返回结构化 JSON。"""


def _run_diagnosis_llm(agent_input: AgentInput, metrics: dict, evidence: list, on_llm_event=None, analysis_context: str = "") -> DiagnosisOutput:
    """使用 LLM 生成诊断结果（OPENAI_BASE_URL 在 llm_client 中生效）"""
    from app.core.llm_client import structured_output, LlmEvent, load_prompt

    logger.info("案件 %s 使用 LLM 路径生成诊断结果", agent_input.case_id)

    system_prompt, _prompt_version = load_prompt("diagnosis_agent", default=DEFAULT_DIAGNOSIS_PROMPT)

    user_prompt = f"""## 案件信息
- 案件编号: {agent_input.case_id}
- 商家ID: {agent_input.merchant_id}

## 商家指标
{json.dumps(metrics, ensure_ascii=False, indent=2)}

## 证据列表
{json.dumps(evidence, ensure_ascii=False, indent=2)}

## 上游分析链路
{analysis_context if analysis_context else '无'}

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