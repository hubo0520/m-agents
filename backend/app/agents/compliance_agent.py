"""
Compliance Guard Agent — 合规校验

校验 Agent 输出是否越权、命中审批规则、schema 校验、敏感词、禁止结论。
扩展 V1/V2 的 guardrail.py，输出 V3 GuardOutput schema。
"""
from typing import List, Optional, Tuple
from app.agents.schemas import (
    GuardOutput, RecommendationOutput, V3ActionRecommendation,
)


# 禁止性关键词
FORBIDDEN_PHRASES = [
    "建议直接放款",
    "建议拒赔",
    "自动放款",
    "自动拒赔",
    "直接拒绝理赔",
    "无需审批",
    "跳过审批",
]

# 必须审批的动作类型
MUST_APPROVE_ACTIONS = [
    "business_loan",
    "advance_settlement",
    "anomaly_review",
    "fraud_review",
    "claim_submission",
]


def run_compliance_guard(
    recommendation_output: dict,
    diagnosis_output: dict = None,
    evidence_output: dict = None,
    on_llm_event=None,
) -> GuardOutput:
    """
    对 Recommendation Agent 的输出进行合规校验。
    支持 LLM 语义增强 + 规则引擎双路径。

    校验规则:
    1. 融资/反欺诈/理赔类建议必须 requires_manual_review=True
    2. 禁止性结论检查（规则 + LLM 语义）
    3. 所有建议必须有 evidence_ids
    4. Schema 结构校验
    5. 超出额度阈值升级审批
    """
    # 先执行规则引擎校验（始终运行）
    rule_result = _run_rule_guard(recommendation_output)

    # 如果 LLM 启用，补充语义级检测
    from app.core.llm_client import is_llm_enabled
    if is_llm_enabled():
        llm_result = _run_llm_semantic_guard(
            recommendation_output, diagnosis_output,
            on_llm_event=on_llm_event,
        )
        if llm_result:
            # 合并 LLM 检测结果到规则引擎结果
            rule_result = _merge_guard_results(rule_result, llm_result)

    return rule_result


def _run_rule_guard(recommendation_output: dict) -> GuardOutput:
    """规则引擎合规校验（原有逻辑）"""
    reason_codes = []
    blocked_actions = []
    passed = True

    try:
        rec_output = RecommendationOutput(**recommendation_output)
    except Exception as e:
        return GuardOutput(
            passed=False,
            reason_codes=["SCHEMA_VALIDATION_FAILED"],
            blocked_actions=[],
            next_state="BLOCKED_BY_GUARD",
            details=f"建议输出 schema 校验失败: {str(e)}",
        )

    for rec in rec_output.recommendations:
        # 规则 1: 必审动作必须标记人工复核
        if rec.action_type in MUST_APPROVE_ACTIONS:
            if not rec.requires_manual_review:
                reason_codes.append("NEEDS_HUMAN_APPROVAL")
                passed = False
                # 自动修复：强制标记
                rec.requires_manual_review = True

        # 规则 2: 禁止性结论检查
        full_text = f"{rec.title} {rec.why}"
        for phrase in FORBIDDEN_PHRASES:
            if phrase in full_text:
                reason_codes.append("FORBIDDEN_CONCLUSION")
                blocked_actions.append(rec.action_type)
                passed = False

        # 规则 3: 建议必须有 evidence_ids
        if not rec.evidence_ids:
            reason_codes.append("MISSING_EVIDENCE_FOR_ACTION")
            blocked_actions.append(rec.action_type)
            passed = False

        # 规则 4: 超出额度阈值升级审批
        if rec.expected_benefit and rec.expected_benefit.cash_relief:
            if rec.expected_benefit.cash_relief > 500000:
                reason_codes.append("EXCEEDS_AMOUNT_THRESHOLD")
                if not rec.requires_manual_review:
                    rec.requires_manual_review = True

    # 去重
    reason_codes = list(set(reason_codes))
    blocked_actions = list(set(blocked_actions))

    # 判断下一状态
    if not passed and blocked_actions:
        next_state = "BLOCKED_BY_GUARD"
    elif any(r.requires_manual_review for r in rec_output.recommendations):
        next_state = "PENDING_APPROVAL"
    else:
        next_state = "EXECUTING"

    return GuardOutput(
        passed=passed,
        reason_codes=reason_codes,
        blocked_actions=blocked_actions,
        next_state=next_state,
        details=f"校验完成：{len(rec_output.recommendations)} 条建议，"
                f"{len(blocked_actions)} 条被阻断",
    )


# ═══════════════════════════════════════════════════════════════
# LLM 语义增强：通过 LLM 检测规则引擎难以覆盖的语义问题
# ═══════════════════════════════════════════════════════════════

import json
from loguru import logger
import re


def _extract_json_from_response(raw: str) -> dict:
    """
    从 LLM 响应中健壮地提取 JSON 对象。

    处理以下情况：
    1. 纯 JSON 字符串
    2. 被 markdown 代码块包裹的 JSON（```json ... ```）
    3. JSON 前后有额外说明文字
    4. None 或空字符串
    """
    if not raw or not raw.strip():
        raise ValueError("LLM 返回了空响应")

    text = raw.strip()

    # 尝试 1：直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试 2：提取 markdown 代码块中的 JSON
    code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 尝试 3：查找第一个 { 到最后一个 } 之间的内容
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"无法从 LLM 响应中提取有效 JSON，原始响应前 200 字符: {text[:200]}")


def _run_llm_semantic_guard(
    recommendation_output: dict,
    diagnosis_output: dict = None,
    on_llm_event=None,
) -> Optional[GuardOutput]:
    """
    使用 LLM 进行语义级合规检测（OPENAI_BASE_URL 在 llm_client 中生效）。

    检测规则引擎无法覆盖的场景：
    - 隐含的禁止性结论（换了说法但语义相同）
    - 建议理由与证据不一致
    - 过度承诺或误导性表述
    - 超出 Agent 职责边界的建议
    """
    from app.core.llm_client import chat_completion_stream, LlmEvent

    logger.info("使用 LLM 路径进行语义级合规校验")

    system_prompt = """你是一个电商平台金融合规审查 Agent，精通《消费者权益保护法》、《电子商务法》和平台内部合规规范。
你的任务是对 Agent 生成的风险保障建议进行语义级合规检测。

## 检测框架（请按以下 4 个维度逐项审查）

**维度 1 — 隐含禁止性结论**：
检查是否存在变相表达以下禁止性结论的语句（包括同义替换、委婉表述）：
- "直接放款" / "自动放款" / "无需审批放款"
- "拒绝理赔" / "直接拒赔" / "不予理赔"
- "无需审批" / "跳过审批" / "自动执行"
⚠️ 注意：如果建议的 why 字段中使用了引导性措辞暗示无需审批流程，也应标记。

**维度 2 — 建议理由合理性**：
- why 字段是否引用了具体数值或证据？（合格示例："退货放大1.8倍" vs 不合格示例："退货异常"）
- why 字段的结论是否能被提供的 evidence 和 diagnosis 支撑？

**维度 3 — 过度承诺检测**：
- expected_benefit 是否使用了绝对化表述：如"保证"、"100%"、"一定"、"完全消除"？
- cash_relief 的金额是否超过了 diagnosis 中的实际评估范围？

**维度 4 — 职责越界检测**：
- 是否包含法律建议（如"建议起诉"、"承担法律责任"）？
- 是否包含投资建议（如"建议投资"、"购买理财"）？
- 是否超出了风控保障的职责范围？

## 反面约束
- ❌ 不要将正常的风险描述误判为禁止性结论（如"建议加速回款"是正常建议，不是禁止性结论）
- ❌ 不要过度检测，只标记真正存在合规风险的问题

请以 JSON 格式返回检测结果：
{
  "has_issues": true/false,
  "issues": [
    {
      "type": "HIDDEN_FORBIDDEN_CONCLUSION" | "UNSUPPORTED_CLAIM" | "OVER_PROMISE" | "OUT_OF_SCOPE",
      "action_type": "相关的动作类型",
      "description": "具体问题描述"
    }
  ]
}

如果没有问题，返回 {"has_issues": false, "issues": []}"""

    recs_text = json.dumps(recommendation_output, ensure_ascii=False, indent=2)
    diag_text = json.dumps(diagnosis_output, ensure_ascii=False, indent=2) if diagnosis_output else "无诊断结果"

    user_prompt = f"""## 建议输出
{recs_text}

## 诊断上下文
{diag_text}

请进行语义合规检测。"""

    try:
        # 发送 llm_input 事件
        if on_llm_event:
            on_llm_event(LlmEvent(
                event_type="llm_input",
                agent_name="compliance_agent",
                step="run_guardrails",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            ))

        import time as _time
        _t0 = _time.time()

        def _on_chunk(delta: str):
            if on_llm_event:
                on_llm_event(LlmEvent(
                    event_type="llm_chunk",
                    agent_name="compliance_agent",
                    step="run_guardrails",
                    content=delta,
                ))

        raw_response = chat_completion_stream(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            on_chunk=_on_chunk,
            temperature=0.1,
            max_tokens=1024,
        )

        _elapsed = int((_time.time() - _t0) * 1000)
        # 发送 llm_done 事件
        if on_llm_event:
            on_llm_event(LlmEvent(
                event_type="llm_done",
                agent_name="compliance_agent",
                step="run_guardrails",
                content=raw_response[:500] if raw_response else "",
                elapsed_ms=_elapsed,
            ))

        logger.debug("LLM 合规检测原始响应: %s", raw_response[:500] if raw_response else "(空)")

        # 健壮地从 LLM 响应中提取 JSON
        result = _extract_json_from_response(raw_response)

        if not result.get("has_issues", False):
            logger.info("LLM 语义合规检测通过")
            return None

        # 将 LLM 检测到的问题转换为 GuardOutput
        reason_codes = []
        blocked_actions = []
        for issue in result.get("issues", []):
            issue_type = issue.get("type", "SEMANTIC_ISSUE")
            reason_codes.append(issue_type)
            action_type = issue.get("action_type")
            if action_type and issue_type in ("HIDDEN_FORBIDDEN_CONCLUSION", "OUT_OF_SCOPE"):
                blocked_actions.append(action_type)

        reason_codes = list(set(reason_codes))
        blocked_actions = list(set(blocked_actions))

        logger.warning(
            "LLM 语义合规检测发现 %d 个问题: %s",
            len(result.get("issues", [])),
            reason_codes,
        )

        return GuardOutput(
            passed=len(blocked_actions) == 0,
            reason_codes=reason_codes,
            blocked_actions=blocked_actions,
            next_state="BLOCKED_BY_GUARD" if blocked_actions else "PENDING_APPROVAL",
            details=f"LLM 语义检测发现 {len(result.get('issues', []))} 个问题",
        )
    except Exception as e:
        logger.error("LLM 语义合规检测失败，仅使用规则引擎结果: %s", e)
        return None


def _merge_guard_results(rule_result: GuardOutput, llm_result: GuardOutput) -> GuardOutput:
    """合并规则引擎和 LLM 语义检测结果"""
    merged_reason_codes = list(set(rule_result.reason_codes + llm_result.reason_codes))
    merged_blocked = list(set(rule_result.blocked_actions + llm_result.blocked_actions))

    # 任一不通过则整体不通过
    passed = rule_result.passed and llm_result.passed

    # 确定下一状态（取最严格的）
    if not passed and merged_blocked:
        next_state = "BLOCKED_BY_GUARD"
    elif any(code in merged_reason_codes for code in ("NEEDS_HUMAN_APPROVAL", "EXCEEDS_AMOUNT_THRESHOLD")):
        next_state = "PENDING_APPROVAL"
    elif rule_result.next_state == "PENDING_APPROVAL" or llm_result.next_state == "PENDING_APPROVAL":
        next_state = "PENDING_APPROVAL"
    else:
        next_state = "EXECUTING"

    return GuardOutput(
        passed=passed,
        reason_codes=merged_reason_codes,
        blocked_actions=merged_blocked,
        next_state=next_state,
        details=f"规则引擎: {rule_result.details} | LLM: {llm_result.details}",
    )


def validate_output_v1(output: dict) -> Tuple[bool, List[str]]:
    """V1/V2 兼容接口：校验旧格式 AgentOutput"""
    from app.agents.schemas import AgentOutput
    errors = []

    try:
        parsed = AgentOutput(**output)
    except Exception as e:
        errors.append(f"JSON Schema 校验失败: {str(e)}")
        return False, errors

    for rec in parsed.recommendations:
        if rec.action_type in ("business_loan", "anomaly_review"):
            if not rec.requires_manual_review:
                errors.append(
                    f"建议 '{rec.title}' (类型={rec.action_type}) "
                    f"必须设置 requires_manual_review=true"
                )

    full_text = parsed.case_summary
    for rec in parsed.recommendations:
        full_text += " " + rec.title + " " + rec.why

    for phrase in FORBIDDEN_PHRASES:
        if phrase in full_text:
            errors.append(f"包含禁止性结论: '{phrase}'")

    for rec in parsed.recommendations:
        if not rec.evidence_ids:
            errors.append(f"建议 '{rec.title}' 缺少 evidence_ids")

    return len(errors) == 0, errors
