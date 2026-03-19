"""
Summary Agent — 案件最终摘要生成

生成最终案件摘要，输出给人类运营和导出系统。
"""
from app.agents.schemas import SummaryOutput, ActionResult


def run_summary(
    diagnosis_output: dict,
    recommendation_output: dict,
    execution_results: list = None,
    guard_output: dict = None,
) -> SummaryOutput:
    """
    基于各 Agent 输出生成案件最终摘要，支持 LLM / 规则引擎双路径。

    Args:
        diagnosis_output: DiagnosisOutput 序列化 dict
        recommendation_output: RecommendationOutput 序列化 dict
        execution_results: 执行动作结果列表
        guard_output: GuardOutput 序列化 dict
    """
    from app.core.llm_client import is_llm_enabled

    if is_llm_enabled():
        return _run_summary_llm(
            diagnosis_output, recommendation_output, execution_results, guard_output
        )

    # ── 规则引擎路径（原有逻辑） ──
    # 构建摘要
    summary_parts = []

    # 从 diagnosis 提取摘要
    business_summary = diagnosis_output.get("business_summary", "")
    if business_summary:
        summary_parts.append(business_summary)

    # 从 recommendations 提取关键建议
    recommendations = recommendation_output.get("recommendations", [])
    if recommendations:
        rec_titles = [r.get("title", "") for r in recommendations]
        summary_parts.append(f"建议措施：{'、'.join(rec_titles)}")

    # 从 guard 提取合规结果
    if guard_output:
        if guard_output.get("passed"):
            summary_parts.append("合规校验通过")
        else:
            blocked = guard_output.get("blocked_actions", [])
            if blocked:
                summary_parts.append(f"合规校验阻断 {len(blocked)} 个动作")

    case_summary = "。".join(summary_parts) + "。" if summary_parts else "暂无摘要信息。"

    # 构建动作结果
    action_results = []
    if execution_results:
        for er in execution_results:
            if isinstance(er, dict):
                action_results.append(ActionResult(**er))
            elif isinstance(er, ActionResult):
                action_results.append(er)
    else:
        # 未执行时根据建议生成 pending 状态
        for rec in recommendations:
            action_results.append(ActionResult(
                action_type=rec.get("action_type", "unknown"),
                status="pending",
                detail=rec.get("title", ""),
            ))

    # 确定最终状态
    if execution_results:
        failed_count = sum(1 for r in action_results if r.status == "failed")
        if failed_count > 0:
            final_status = "COMPLETED_WITH_ERRORS"
        else:
            final_status = "COMPLETED"
    elif guard_output and not guard_output.get("passed"):
        final_status = "BLOCKED_BY_GUARD"
    else:
        final_status = "COMPLETED"

    return SummaryOutput(
        case_summary=case_summary,
        action_results=action_results,
        final_status=final_status,
    )


# ═══════════════════════════════════════════════════════════════
# LLM 路径：通过 LLM 生成案件摘要
# ═══════════════════════════════════════════════════════════════

import json
import logging

logger = logging.getLogger(__name__)


def _run_summary_llm(
    diagnosis_output: dict,
    recommendation_output: dict,
    execution_results: list = None,
    guard_output: dict = None,
) -> SummaryOutput:
    """使用 LLM 生成案件摘要（OPENAI_BASE_URL 在 llm_client 中生效）"""
    from app.core.llm_client import chat_completion

    logger.info("使用 LLM 路径生成案件摘要")

    system_prompt = """你是一个电商平台风险运营助手。
你的任务是根据案件的诊断结果、建议措施、执行结果和合规校验结果，生成一份简洁的案件摘要。

要求：
1. 用中文输出，简洁专业
2. 摘要不超过200字
3. 重点说明：风险类型、关键指标、采取的措施、当前状态"""

    user_prompt = f"""## 诊断结果
{json.dumps(diagnosis_output, ensure_ascii=False, indent=2)}

## 建议措施
{json.dumps(recommendation_output, ensure_ascii=False, indent=2)}

## 执行结果
{json.dumps(execution_results, ensure_ascii=False, indent=2) if execution_results else "尚未执行"}

## 合规校验
{json.dumps(guard_output, ensure_ascii=False, indent=2) if guard_output else "未进行合规校验"}

请生成案件摘要。"""

    try:
        summary_text = chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=512,
        )

        # 构建动作结果（复用原有逻辑）
        action_results = _build_action_results(
            recommendation_output, execution_results
        )
        final_status = _determine_final_status(
            execution_results, guard_output, action_results
        )

        logger.info("LLM 案件摘要生成完成")
        return SummaryOutput(
            case_summary=summary_text.strip(),
            action_results=action_results,
            final_status=final_status,
        )
    except Exception as e:
        logger.error("LLM 案件摘要生成失败，回退规则引擎: %s", e)
        return run_summary(diagnosis_output, recommendation_output, execution_results, guard_output)


def _build_action_results(recommendation_output: dict, execution_results: list = None) -> list:
    """构建动作结果列表（LLM 和规则引擎共享）"""
    action_results = []
    recommendations = recommendation_output.get("recommendations", [])
    if execution_results:
        for er in execution_results:
            if isinstance(er, dict):
                action_results.append(ActionResult(**er))
            elif isinstance(er, ActionResult):
                action_results.append(er)
    else:
        for rec in recommendations:
            action_results.append(ActionResult(
                action_type=rec.get("action_type", "unknown"),
                status="pending",
                detail=rec.get("title", ""),
            ))
    return action_results


def _determine_final_status(execution_results, guard_output, action_results) -> str:
    """确定最终状态（LLM 和规则引擎共享）"""
    if execution_results:
        failed_count = sum(1 for r in action_results if r.status == "failed")
        return "COMPLETED_WITH_ERRORS" if failed_count > 0 else "COMPLETED"
    elif guard_output and not guard_output.get("passed"):
        return "BLOCKED_BY_GUARD"
    return "COMPLETED"