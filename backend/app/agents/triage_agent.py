"""
Triage Agent — 案件分类与优先级判定（Hybrid 架构）

三级决策架构：
- Level 1（确定区间）：纯规则，零延迟
- Level 2（模糊区间）：LLM 精细分类
- Level 3（安全网）：后处理校验 LLM 输出
"""
import json
from loguru import logger

from app.agents.schemas import (
    AgentInput, TriageOutput, CaseType, Priority,
)


def run_triage(agent_input: AgentInput, metrics: dict, case_context: dict, on_llm_event=None) -> TriageOutput:
    """
    Hybrid 三级决策架构：

    Level 1 — 确定区间（纯规则）:
    - anomaly_score >= 0.8 → 直接判定 SUSPECTED_FRAUD, HIGH
    - anomaly_score <= 0.1 且 predicted_gap == 0 → 直接判定 CASH_GAP, LOW

    Level 2 — 模糊区间（LLM 精细分类）:
    - 其他情况，交给 LLM 进行复合风险识别

    Level 3 — 安全网（后处理校验）:
    - 校验 LLM 输出的 case_type 和 priority 合法性
    """
    anomaly_score = metrics.get("anomaly_score", 0)
    predicted_gap = metrics.get("predicted_gap", 0)

    # ── Level 1: 确定区间 — 纯规则，零延迟 ──
    level1_result = _level1_rule_filter(anomaly_score, predicted_gap, metrics, case_context)
    if level1_result is not None:
        logger.info(
            "案件 %s Level 1 规则判定: case_type=%s, priority=%s",
            agent_input.case_id, level1_result.case_type.value, level1_result.priority.value,
        )
        return level1_result

    # ── Level 2: 模糊区间 — LLM 精细分类 ──
    from app.core.llm_client import is_llm_enabled
    if is_llm_enabled():
        try:
            llm_result = _level2_llm_classify(agent_input, metrics, case_context, on_llm_event=on_llm_event)
            # ── Level 3: 安全网 — 校验 LLM 输出合法性 ──
            validated = _level3_safety_net(llm_result)
            logger.info(
                "案件 %s Level 2 LLM 判定: case_type=%s, priority=%s",
                agent_input.case_id, validated.case_type.value, validated.priority.value,
            )
            return validated
        except Exception as e:
            logger.warning("案件 %s LLM 分诊失败，回退规则引擎: %s", agent_input.case_id, e)

    # ── Fallback: 原有规则引擎 ──
    return _rule_engine_fallback(metrics, case_context)


def _level1_rule_filter(anomaly_score: float, predicted_gap: float, metrics: dict, case_context: dict) -> TriageOutput | None:
    """Level 1: 确定区间规则预过滤"""

    # 高确定性：异常分数极高 → 直接判定欺诈
    if anomaly_score >= 0.8:
        return TriageOutput(
            case_type=CaseType.SUSPECTED_FRAUD,
            priority=Priority.HIGH,
            recommended_path="evidence → guardrails → fraud_review",
            reasoning=f"异常退货分数 {anomaly_score:.2f} >= 0.8，确定性高，直接判定疑似欺诈",
        )

    # 高确定性：极低风险 → 直接判定 LOW
    if anomaly_score <= 0.1 and predicted_gap == 0:
        return TriageOutput(
            case_type=CaseType.CASH_GAP,
            priority=Priority.LOW,
            recommended_path="forecast → diagnosis → recommendations",
            reasoning=f"异常分数 {anomaly_score:.2f} <= 0.1 且无预测缺口，风险极低",
        )

    return None  # 模糊区间，交给 Level 2


def _level2_llm_classify(agent_input: AgentInput, metrics: dict, case_context: dict, on_llm_event=None) -> TriageOutput:
    """Level 2: LLM 精细分类（模糊区间）"""
    from app.core.llm_client import structured_output, LlmEvent, load_prompt

    DEFAULT_TRIAGE_PROMPT = """你是一个电商平台风险案件分诊专家。你需要根据商家的经营指标和案件上下文，精确判断案件类型和优先级。

## 案件类型 (case_type)
- cash_gap: 现金缺口 — 商家面临流动性风险，退货/回款导致资金紧张
- suspected_fraud: 疑似欺诈 — 存在异常退货模式或其他欺诈信号
- business_loan: 经营贷需求 — 经营稳定但需要融资补充现金流
- insurance_claim: 保险理赔 — 有保单且满足理赔条件

## 优先级 (priority)
- high: 需要立即处理（严重欺诈风险/大额资金缺口/多重风险叠加）
- medium: 需要关注（中等风险信号/单一维度异常）
- low: 例行处理（轻微异常/预防性监控）

## 推理要求
- reasoning 字段必须说明判断依据，引用具体指标数值
- 当同时存在多种风险信号时（如退货异常 + 资金缺口），选择最高风险的 case_type
- recommended_path 应根据 case_type 给出处理链路

## 反面约束
- ❌ 不要仅凭单一指标就判定 high 优先级
- ❌ anomaly_score 在 0.3~0.5 之间时不要直接判定 suspected_fraud，需结合退货模式综合判断

请严格按照输出 Schema 返回结构化 JSON。"""

    system_prompt, _prompt_version = load_prompt("triage_agent", default=DEFAULT_TRIAGE_PROMPT)

    user_prompt = f"""## 案件信息
- 案件编号: {agent_input.case_id}
- 商家ID: {agent_input.merchant_id}

## 商家指标
{json.dumps(metrics, ensure_ascii=False, indent=2)}

## 案件上下文
{json.dumps(case_context, ensure_ascii=False, indent=2)}

请进行案件分类和优先级判定。"""

    # 发送 llm_input 事件
    if on_llm_event:
        on_llm_event(LlmEvent(
            event_type="llm_input",
            agent_name="triage_agent",
            step="triage_case",
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
        response_model=TriageOutput,
    )

    _elapsed = int((_time.time() - _t0) * 1000)
    if on_llm_event:
        on_llm_event(LlmEvent(
            event_type="llm_done",
            agent_name="triage_agent",
            step="triage_case",
            content=result.reasoning[:500] if result.reasoning else "",
            elapsed_ms=_elapsed,
        ))

    return result


def _level3_safety_net(result: TriageOutput) -> TriageOutput:
    """Level 3: 安全网 — 校验 LLM 输出合法性"""
    # 校验 case_type 是否在枚举中（structured_output 已保证，但双重保险）
    valid_case_types = {ct.value for ct in CaseType}
    if result.case_type.value not in valid_case_types:
        logger.warning("LLM 输出非法 case_type=%s，回退为 cash_gap", result.case_type)
        result.case_type = CaseType.CASH_GAP

    valid_priorities = {p.value for p in Priority}
    if result.priority.value not in valid_priorities:
        logger.warning("LLM 输出非法 priority=%s，回退为 medium", result.priority)
        result.priority = Priority.MEDIUM

    return result


def _rule_engine_fallback(metrics: dict, case_context: dict) -> TriageOutput:
    """原有规则引擎（Fallback / LLM 未启用时使用）"""
    anomaly_score = metrics.get("anomaly_score", 0)
    return_amplification = metrics.get("return_amplification", 0)
    predicted_gap = metrics.get("predicted_gap", 0)
    has_insurance = case_context.get("has_insurance", False)
    operation_days = case_context.get("operation_days", 0)

    # 优先级判定
    if anomaly_score >= 0.8 or (return_amplification >= 2.0 and predicted_gap >= 100000):
        priority = Priority.HIGH
    elif anomaly_score >= 0.5 or return_amplification >= 1.6 or predicted_gap >= 50000:
        priority = Priority.MEDIUM
    else:
        priority = Priority.LOW

    # 案件类型判定
    if anomaly_score >= 0.5:
        case_type = CaseType.SUSPECTED_FRAUD
        recommended_path = "evidence → guardrails → fraud_review"
        reasoning = f"异常退货分数 {anomaly_score:.2f} >= 0.5，疑似欺诈，需人工复核"
    elif has_insurance and predicted_gap > 0:
        case_type = CaseType.INSURANCE_CLAIM
        recommended_path = "diagnosis → evidence → claim_draft"
        reasoning = f"商家有保单且存在缺口 ¥{predicted_gap:,.0f}，建议走理赔路径"
    elif operation_days >= 60 and predicted_gap >= 50000:
        case_type = CaseType.BUSINESS_LOAN
        recommended_path = "diagnosis → forecast → loan_draft"
        reasoning = f"经营 {operation_days} 天，缺口 ¥{predicted_gap:,.0f}，建议经营贷"
    elif return_amplification >= 1.3 and predicted_gap > 0:
        case_type = CaseType.CASH_GAP
        recommended_path = "forecast → diagnosis → advance_settlement"
        reasoning = f"退货放大 {return_amplification:.1f}x，缺口 ¥{predicted_gap:,.0f}，走回款加速"
    else:
        case_type = CaseType.CASH_GAP
        recommended_path = "forecast → diagnosis → recommendations"
        reasoning = "默认走现金缺口分析路径"

    return TriageOutput(
        case_type=case_type,
        priority=priority,
        recommended_path=recommended_path,
        reasoning=reasoning,
    )