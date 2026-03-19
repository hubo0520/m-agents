"""
Triage Agent — 案件分类与优先级判定

根据案件上下文判断 case_type 和 priority，决定走哪条 graph 分支。
非 LLM Agent，由规则 + 指标驱动。
"""
from app.agents.schemas import (
    AgentInput, TriageOutput, CaseType, Priority,
)


def run_triage(agent_input: AgentInput, metrics: dict, case_context: dict) -> TriageOutput:
    """
    根据案件上下文和指标进行分类。

    分类规则:
    - 异常退货分数 >= 0.5 → suspected_fraud
    - 退货放大率 >= 1.3 且预测缺口 > 0 → cash_gap
    - 经营天数 >= 60 且预测缺口 >= 50000 → business_loan
    - 有保单且理赔条件满足 → insurance_claim
    - 默认 → cash_gap
    """
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
