"""
证据 Agent（Mock 实现）

为案件收集证据，生成 evidence_id 映射。
"""
from datetime import datetime
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

    cutoff_7d = datetime.utcnow() - timedelta(days=7)
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


def run_evidence(agent_input: AgentInput, db: Session, case: RiskCase) -> EvidenceOutput:
    """V3 适配器：将现有证据收集逻辑包装为 EvidenceOutput"""
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

    return EvidenceOutput(
        evidence_bundle=bundles,
        coverage_summary=f"共收集 {len(bundles)} 条证据",
        total_evidence_count=len(bundles),
    )
