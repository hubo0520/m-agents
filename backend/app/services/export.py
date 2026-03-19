"""
案件导出服务 — Markdown / JSON 格式
"""
import json
from sqlalchemy.orm import Session

from app.models.models import (
    RiskCase, Merchant, EvidenceItem, Recommendation, Review, AuditLog,
)


def export_case_markdown(db: Session, case_id: int) -> str:
    """导出案件为 Markdown 格式"""
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        raise ValueError(f"案件 #{case_id} 不存在")

    merchant = db.query(Merchant).filter(Merchant.id == case.merchant_id).first()
    evidence = db.query(EvidenceItem).filter(EvidenceItem.case_id == case_id).all()
    recommendations = db.query(Recommendation).filter(Recommendation.case_id == case_id).all()
    reviews = db.query(Review).filter(Review.case_id == case_id).all()
    audit_logs = db.query(AuditLog).filter(
        AuditLog.entity_type == "risk_case",
        AuditLog.entity_id == case_id,
    ).order_by(AuditLog.created_at.desc()).all()

    agent_output = json.loads(case.agent_output_json) if case.agent_output_json else {}

    lines = [
        f"# 风险案件报告 — RC-{case.id:04d}",
        "",
        "## 商家概况",
        f"- **商家名称**: {merchant.name}" if merchant else "- 未知商家",
        f"- **行业**: {merchant.industry}" if merchant else "",
        f"- **店铺等级**: {merchant.store_level}" if merchant else "",
        f"- **结算周期**: {merchant.settlement_cycle_days}天" if merchant else "",
        "",
        "## 风险结论",
        f"- **风险等级**: {case.risk_level}",
        f"- **风险分数**: {case.risk_score}",
        f"- **案件状态**: {case.status}",
        f"- **摘要**: {agent_output.get('case_summary', '暂无')}",
        "",
    ]

    # 根因
    root_causes = agent_output.get("root_causes", [])
    if root_causes:
        lines.append("### 核心成因")
        for i, rc in enumerate(root_causes, 1):
            lines.append(f"{i}. **{rc.get('label', '')}**: {rc.get('explanation', '')}"
                        f" (置信度: {rc.get('confidence', 0):.0%})")
        lines.append("")

    # 现金缺口
    forecast = agent_output.get("cash_gap_forecast", {})
    if forecast:
        lines.extend([
            "## 14日缺口预测",
            f"- **预测缺口**: ¥{forecast.get('predicted_gap', 0):,.0f}",
            f"- **最低现金日**: {forecast.get('lowest_cash_day', '无')}",
            f"- **置信度**: {forecast.get('confidence', 0):.0%}",
            "",
        ])

    # 建议
    recs = agent_output.get("recommendations", [])
    if recs:
        lines.append("## 动作建议")
        for i, rec in enumerate(recs, 1):
            review_tag = " 🔍需人工复核" if rec.get("requires_manual_review") else ""
            lines.append(f"{i}. **{rec.get('title', '')}**{review_tag}")
            lines.append(f"   - 原因: {rec.get('why', '')}")
            lines.append(f"   - 预期收益: {rec.get('expected_benefit', '')}")
            lines.append(f"   - 置信度: {rec.get('confidence', 0):.0%}")
        lines.append("")

    # 证据
    if evidence:
        lines.append("## 证据列表")
        for ev in evidence:
            lines.append(f"- [{ev.evidence_type}] {ev.summary}")
        lines.append("")

    # 审批记录
    if reviews:
        lines.append("## 审批记录")
        for rv in reviews:
            lines.append(f"- **{rv.decision}** by {rv.reviewer_id} ({rv.created_at})")
            if rv.comment:
                lines.append(f"  意见: {rv.comment}")
        lines.append("")

    return "\n".join(lines)


def export_case_json(db: Session, case_id: int) -> dict:
    """导出案件为 JSON 格式"""
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        raise ValueError(f"案件 #{case_id} 不存在")

    merchant = db.query(Merchant).filter(Merchant.id == case.merchant_id).first()
    evidence = db.query(EvidenceItem).filter(EvidenceItem.case_id == case_id).all()
    reviews = db.query(Review).filter(Review.case_id == case_id).all()
    audit_logs = db.query(AuditLog).filter(
        AuditLog.entity_type == "risk_case",
        AuditLog.entity_id == case_id,
    ).order_by(AuditLog.created_at.desc()).all()

    agent_output = json.loads(case.agent_output_json) if case.agent_output_json else {}

    return {
        "case_id": f"RC-{case.id:04d}",
        "merchant": {
            "id": merchant.id,
            "name": merchant.name,
            "industry": merchant.industry,
            "store_level": merchant.store_level,
            "settlement_cycle_days": merchant.settlement_cycle_days,
        } if merchant else None,
        "risk_level": case.risk_level,
        "risk_score": case.risk_score,
        "status": case.status,
        "agent_output": agent_output,
        "evidence": [
            {
                "id": ev.id,
                "type": ev.evidence_type,
                "summary": ev.summary,
                "importance_score": ev.importance_score,
            }
            for ev in evidence
        ],
        "reviews": [
            {
                "decision": rv.decision,
                "reviewer_id": rv.reviewer_id,
                "comment": rv.comment,
                "created_at": str(rv.created_at) if rv.created_at else None,
            }
            for rv in reviews
        ],
        "audit_logs": [
            {
                "action": al.action,
                "actor": al.actor,
                "old_value": al.old_value,
                "new_value": al.new_value,
                "created_at": str(al.created_at) if al.created_at else None,
            }
            for al in audit_logs
        ],
    }
