"""
守卫规则引擎

校验 Agent 输出的合规性。
"""
from app.agents.schemas import AgentOutput
from typing import List, Tuple


# 禁止性关键词
FORBIDDEN_PHRASES = [
    "建议直接放款",
    "建议拒赔",
    "自动放款",
    "自动拒赔",
    "直接拒绝理赔",
]


def validate_output(output: dict) -> Tuple[bool, List[str]]:
    """
    校验 Agent 输出。
    返回 (is_valid, errors)
    """
    errors = []

    # 1. JSON Schema 校验
    try:
        parsed = AgentOutput(**output)
    except Exception as e:
        errors.append(f"JSON Schema 校验失败: {str(e)}")
        return False, errors

    # 2. 融资/反欺诈类建议必须 requires_manual_review=True
    for rec in parsed.recommendations:
        if rec.action_type in ("business_loan", "anomaly_review"):
            if not rec.requires_manual_review:
                errors.append(
                    f"建议 '{rec.title}' (类型={rec.action_type}) "
                    f"必须设置 requires_manual_review=true"
                )

    # 3. 禁止性结论检查
    full_text = parsed.case_summary
    for rec in parsed.recommendations:
        full_text += " " + rec.title + " " + rec.why

    for phrase in FORBIDDEN_PHRASES:
        if phrase in full_text:
            errors.append(f"包含禁止性结论: '{phrase}'")

    # 4. 所有建议必须有 evidence_ids
    for rec in parsed.recommendations:
        if not rec.evidence_ids:
            errors.append(f"建议 '{rec.title}' 缺少 evidence_ids")

    is_valid = len(errors) == 0
    return is_valid, errors


# ═══════════════════════════════════════════════════════════════
# V3: GuardOutput 格式适配
# ═══════════════════════════════════════════════════════════════

from app.agents.schemas import GuardOutput


def validate_output_v3(output: dict) -> GuardOutput:
    """V3 适配器：将校验结果包装为 GuardOutput"""
    is_valid, errors = validate_output(output)

    reason_codes = []
    blocked_actions = []
    for err in errors:
        if "requires_manual_review" in err:
            reason_codes.append("NEEDS_HUMAN_APPROVAL")
        elif "禁止性结论" in err:
            reason_codes.append("FORBIDDEN_CONCLUSION")
        elif "evidence_ids" in err:
            reason_codes.append("MISSING_EVIDENCE")
        elif "Schema" in err:
            reason_codes.append("SCHEMA_VALIDATION_FAILED")

    return GuardOutput(
        passed=is_valid,
        reason_codes=reason_codes,
        blocked_actions=blocked_actions,
        next_state="PENDING_APPROVAL" if is_valid else "BLOCKED_BY_GUARD",
        details="; ".join(errors) if errors else "校验通过",
    )
