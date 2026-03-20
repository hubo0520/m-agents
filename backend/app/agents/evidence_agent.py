"""
证据 Agent（Mock 实现）

为案件收集证据，生成 evidence_id 映射。
"""
from datetime import datetime
from app.core.utils import utc_now
from sqlalchemy.orm import Session
from typing import List

from app.models.models import (
    RiskCase, Order, Return, Settlement, EvidenceItem, Merchant,
)


def collect_evidence(db: Session, case: RiskCase) -> List[dict]:
    """
    收集支撑案件结论的证据。
    返回 evidence 列表，每条包含 evidence_id、类型和摘要。
    """
    evidences = []
    merchant_id = case.merchant_id
    ev_counter = 100

    # 1. 高退货率订单证据
    from sqlalchemy import func
    from datetime import timedelta

    cutoff_7d = utc_now() - timedelta(days=7)
    recent_returns = (
        db.query(Return, Order)
        .join(Order, Return.order_id == Order.id)
        .filter(Order.merchant_id == merchant_id, Return.return_time >= cutoff_7d)
        .order_by(Return.refund_amount.desc())
        .limit(5)
        .all()
    )

    for ret, order in recent_returns:
        ev_counter += 1
        ev_id = f"EV-{ev_counter}"
        ev = EvidenceItem(
            case_id=case.id,
            evidence_type="return",
            source_table="returns",
            source_id=ret.id,
            summary=f"订单#{order.id}退货，原因: {ret.return_reason}，退款: ¥{ret.refund_amount:.2f}",
            importance_score=0.8,
        )
        db.add(ev)
        evidences.append({
            "evidence_id": ev_id,
            "type": "return",
            "summary": ev.summary,
            "db_id": None,  # flush 后更新
        })

    # 2. 回款延迟证据
    delayed_settlements = (
        db.query(Settlement)
        .filter(
            Settlement.merchant_id == merchant_id,
            Settlement.actual_settlement_date.isnot(None),
        )
        .order_by(Settlement.expected_settlement_date.desc())
        .limit(3)
        .all()
    )

    for s in delayed_settlements:
        if s.actual_settlement_date and s.expected_settlement_date:
            delay = (s.actual_settlement_date - s.expected_settlement_date).days
            if delay > 0:
                ev_counter += 1
                ev_id = f"EV-{ev_counter}"
                ev = EvidenceItem(
                    case_id=case.id,
                    evidence_type="settlement",
                    source_table="settlements",
                    source_id=s.id,
                    summary=f"回款 #{s.id} 延迟 {delay} 天，金额: ¥{s.amount:.2f}",
                    importance_score=0.7,
                )
                db.add(ev)
                evidences.append({
                    "evidence_id": ev_id,
                    "type": "settlement",
                    "summary": ev.summary,
                })

    # 3. 规则命中证据
    import json

    # 规则名 → 中文映射
    RULE_NAME_MAP = {
        "return_rate_7d":        "近7日退货率",
        "return_rate_14d":       "近14日退货率",
        "return_rate_28d":       "近28日退货率",
        "settlement_delay_days": "回款延迟天数",
        "return_amplification":  "退货放大倍数",
        "cash_gap":              "现金缺口",
        "order_amount":          "订单金额",
        "refund_amount":         "退款金额",
    }

    def _format_rule_value(rule_key: str, value) -> str:
        """根据规则类型格式化展示值"""
        if value is None or value == "N/A":
            return "N/A"
        # 比率类规则：转百分比
        if "rate" in rule_key:
            try:
                return f"{float(value):.2%}"
            except (ValueError, TypeError):
                return str(value)
        # 倍数类规则
        if "amplification" in rule_key:
            try:
                return f"{float(value):.2f}x"
            except (ValueError, TypeError):
                return str(value)
        # 金额类规则
        if "amount" in rule_key or "gap" in rule_key:
            try:
                return f"¥{float(value):,.2f}"
            except (ValueError, TypeError):
                return str(value)
        # 天数类规则
        if "delay" in rule_key or "days" in rule_key:
            return f"{value}天"
        return str(value)

    if case.trigger_json:
        raw = json.loads(case.trigger_json)

        # 兼容两种格式：
        # - 正式格式（risk_scanner）: [{"rule": "...", "value": ...}, ...]
        # - Mock 格式: {"type": "auto_monitor", "return_rate_7d": 0.25, ...}
        if isinstance(raw, list):
            triggers = raw
        elif isinstance(raw, dict):
            # 将字典转换为标准触发规则列表
            triggers = []
            for key, val in raw.items():
                if key in ("type", "scenario"):
                    continue  # 跳过元数据字段
                triggers.append({"rule": key, "value": val})
        else:
            triggers = []

        for trigger in triggers:
            if not isinstance(trigger, dict) or "rule" not in trigger:
                continue  # 跳过格式不合法的条目
            ev_counter += 1
            ev_id = f"EV-{ev_counter}"
            rule_key = trigger['rule']
            rule_label = RULE_NAME_MAP.get(rule_key, rule_key)
            formatted_value = _format_rule_value(rule_key, trigger.get('value', 'N/A'))
            ev = EvidenceItem(
                case_id=case.id,
                evidence_type="rule_hit",
                source_table="risk_cases",
                source_id=case.id,
                summary=f"触发规则: {rule_label}，值={formatted_value}",
                importance_score=0.9,
            )
            db.add(ev)
            evidences.append({
                "evidence_id": ev_id,
                "type": "rule_hit",
                "summary": ev.summary,
            })

    db.flush()
    return evidences


# ═══════════════════════════════════════════════════════════════
# V3 适配器：将 collect_evidence 输出适配为 EvidenceOutput
# ═══════════════════════════════════════════════════════════════

from app.agents.schemas import AgentInput, EvidenceOutput, EvidenceBundle


def run_evidence(agent_input: AgentInput, db: Session, case: RiskCase, on_llm_event=None, analysis_context: str = "") -> EvidenceOutput:
    """
    V3 适配器：两阶段架构

    Phase 1（SQL 收集，不变）→ Phase 2（LLM 分析，新增）
    当证据数量 > 3 且 LLM 启用时触发 Phase 2。
    """
    # ── Phase 1: SQL 收集 ──
    raw_evidences = collect_evidence(db, case)

    bundles = []
    for ev in raw_evidences:
        bundles.append(EvidenceBundle(
            evidence_id=ev["evidence_id"],
            evidence_type=ev["type"],
            summary=ev.get("summary", ""),
            source_table=None,
            source_id=None,
            importance_score=0.7,
        ))

    phase1_output = EvidenceOutput(
        evidence_bundle=bundles,
        coverage_summary=f"共收集 {len(bundles)} 条证据",
        total_evidence_count=len(bundles),
    )

    # ── Phase 2: LLM 分析（条件触发） ──
    from app.core.llm_client import is_llm_enabled
    if is_llm_enabled() and len(bundles) > 3:
        try:
            return _analyze_evidence_llm(
                phase1_output, analysis_context,
                on_llm_event=on_llm_event,
            )
        except Exception as e:
            from loguru import logger
            logger.warning("Evidence LLM 分析失败，保留 Phase 1 结果: %s", e)

    return phase1_output


# ═══════════════════════════════════════════════════════════════
# Phase 2: LLM 证据分析层
# ═══════════════════════════════════════════════════════════════

import json as _json
from loguru import logger as _logger


def _analyze_evidence_llm(
    evidence_output: EvidenceOutput,
    analysis_context: str = "",
    on_llm_event=None,
) -> EvidenceOutput:
    """
    LLM 证据分析层：

    1. 动态评估每条证据的 importance_score（基于案件上下文）
    2. 发现证据间关联模式
    3. 生成有洞察的 coverage_summary
    """
    from app.core.llm_client import chat_completion, LlmEvent

    system_prompt = """你是一个电商平台证据分析专家。你的任务是分析已收集的证据列表，完成以下 3 项工作：

1. **动态评分**：为每条证据重新评估 importance_score (0~1)，基于案件上下文而非固定值。
   - 如果案件类型为疑似欺诈：退货类证据得分应更高
   - 如果案件类型为现金缺口：回款延迟类证据得分应更高

2. **关联模式**：识别证据间的关联模式（如：多条退货+回款延迟=现金流恶化链）

3. **覆盖摘要**：生成一段有洞察的摘要（不超过 100 字），替代简单的"共收集 N 条证据"

请以 JSON 格式返回：
{
  "scores": {"EV-101": 0.85, "EV-102": 0.7, ...},
  "patterns": "退货集中爆发与回款延迟同步出现，形成现金流恶化链",
  "summary": "共收集8条证据，其中5条退货证据显示近7日集中退货，2条回款延迟证据与退货时间窗口重叠，形成现金流恶化链条"
}"""

    bundles_data = []
    for b in evidence_output.evidence_bundle:
        bundles_data.append({
            "evidence_id": b.evidence_id,
            "type": b.evidence_type,
            "summary": b.summary,
        })

    user_prompt = f"""## 证据列表
{_json.dumps(bundles_data, ensure_ascii=False, indent=2)}

## 上游分析链路
{analysis_context if analysis_context else '无'}

请分析以上证据。"""

    if on_llm_event:
        on_llm_event(LlmEvent(
            event_type="llm_input",
            agent_name="evidence_agent",
            step="collect_evidence",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        ))

    import time as _time
    _t0 = _time.time()

    raw_response = chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=1024,
    )

    _elapsed = int((_time.time() - _t0) * 1000)
    if on_llm_event:
        on_llm_event(LlmEvent(
            event_type="llm_done",
            agent_name="evidence_agent",
            step="collect_evidence",
            content=raw_response[:500] if raw_response else "",
            elapsed_ms=_elapsed,
        ))

    # 解析 LLM 响应
    import re
    text = raw_response.strip()
    # 尝试提取 JSON
    code_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if code_block:
        text = code_block.group(1).strip()
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace > first_brace:
        text = text[first_brace:last_brace + 1]

    result = _json.loads(text)
    scores = result.get("scores", {})
    summary = result.get("summary", evidence_output.coverage_summary)
    patterns = result.get("patterns", "")

    # 用 LLM 返回的分数更新 importance_score
    for bundle in evidence_output.evidence_bundle:
        if bundle.evidence_id in scores:
            bundle.importance_score = max(0.0, min(1.0, float(scores[bundle.evidence_id])))

    # 更新 coverage_summary
    if patterns:
        evidence_output.coverage_summary = f"{summary}。关联模式: {patterns}"
    else:
        evidence_output.coverage_summary = summary

    _logger.info("Evidence LLM 分析完成: %d 条证据已重新评分", len(scores))
    return evidence_output
