"""
Orchestrator — Agent 编排层

协调指标计算→证据收集→摘要生成→建议生成→守卫校验的完整流程。
"""
import json
import traceback
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.models import RiskCase, Merchant, Recommendation
from app.engine.metrics import get_all_metrics
from app.engine.cashflow import forecast_cash_gap
from app.agents.evidence_agent import collect_evidence
from app.agents.analysis_agent import generate_summary
from app.agents.recommend_agent import generate_recommendations
from app.agents.guardrail import validate_output
from app.agents.schemas import AgentOutput
from app.services.task_generator import generate_tasks_for_case


def analyze(db: Session, case_id: int) -> dict:
    """
    对指定案件执行完整分析流程。

    流程:
    1. 计算商家指标
    2. 收集证据
    3. 生成摘要
    4. 生成建议
    5. 守卫校验
    6. 保存到数据库

    异常时回退到"结构化指标 + 规则建议"模式。
    """
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        raise ValueError(f"案件 #{case_id} 不存在")

    merchant = db.query(Merchant).filter(Merchant.id == case.merchant_id).first()
    if not merchant:
        raise ValueError(f"商家 #{case.merchant_id} 不存在")

    try:
        # 1. 计算指标
        metrics = get_all_metrics(db, merchant.id)

        # 2. 现金缺口预测
        forecast = forecast_cash_gap(db, merchant.id, horizon_days=14)
        predicted_gap = forecast["predicted_gap"]
        metrics["predicted_gap"] = predicted_gap

        # 3. 收集证据
        evidence = collect_evidence(db, case)

        # 4. 生成摘要
        summary = generate_summary(metrics, evidence)

        # 5. 生成建议
        recommendations = generate_recommendations(
            db, merchant, metrics, predicted_gap, evidence
        )

        # 6. 组装 Agent 输出
        agent_output = {
            "case_id": f"RC-{case.id:04d}",
            "risk_level": summary["risk_level"],
            "case_summary": summary["case_summary"],
            "root_causes": summary["root_causes"],
            "cash_gap_forecast": {
                "horizon_days": 14,
                "predicted_gap": predicted_gap,
                "lowest_cash_day": forecast.get("lowest_cash_day"),
                "confidence": forecast.get("confidence", 0.5),
            },
            "recommendations": recommendations,
            "manual_review_required": summary["manual_review_required"],
        }

        # 7. 守卫校验
        is_valid, errors = validate_output(agent_output)
        if not is_valid:
            print(f"⚠️ 守卫校验发现问题: {errors}")
            # 尝试自动修复
            for rec in agent_output["recommendations"]:
                if rec["action_type"] in ("business_loan", "anomaly_review"):
                    rec["requires_manual_review"] = True
            # 重新校验
            is_valid, errors = validate_output(agent_output)
            if not is_valid:
                raise ValueError(f"守卫校验失败: {errors}")

        # 8. 保存到数据库
        case.agent_output_json = json.dumps(agent_output, ensure_ascii=False)
        case.risk_level = summary["risk_level"]
        case.risk_score = _compute_risk_score_from_metrics(metrics, predicted_gap)
        case.status = "ANALYZED"
        case.updated_at = datetime.utcnow()

        # 保存推荐到 recommendations 表
        for rec_data in recommendations:
            rec = Recommendation(
                case_id=case.id,
                action_type=rec_data["action_type"],
                content_json=json.dumps(rec_data, ensure_ascii=False),
                confidence=rec_data.get("confidence", 0),
                requires_manual_review=1 if rec_data.get("requires_manual_review") else 0,
            )
            db.add(rec)

        db.flush()

        # V2: 分析完成后自动调用任务生成引擎
        try:
            tasks_generated = generate_tasks_for_case(db, case_id)
            if tasks_generated:
                print(f"✅ 案件 #{case_id} 自动生成 {len(tasks_generated)} 条执行任务")
        except Exception as task_err:
            print(f"⚠️ 任务生成失败（不影响分析结果）: {task_err}")

        return agent_output

    except Exception as e:
        # 回退到"结构化指标 + 规则建议"模式
        print(f"⚠️ Agent 分析失败，回退到规则模式: {e}")
        traceback.print_exc()
        return _fallback_analysis(db, case, merchant)


def _compute_risk_score_from_metrics(metrics: dict, predicted_gap: float) -> float:
    """从指标计算综合风险分数"""
    score = 0.0
    amp = metrics.get("return_amplification", 0)
    if amp >= 2.0:
        score += 30
    elif amp >= 1.6:
        score += 20
    elif amp >= 1.3:
        score += 10

    if predicted_gap >= 100000:
        score += 30
    elif predicted_gap >= 50000:
        score += 20
    elif predicted_gap >= 20000:
        score += 10

    delay = metrics.get("avg_settlement_delay", 0)
    if delay >= 5:
        score += 20
    elif delay >= 3:
        score += 15
    elif delay >= 2:
        score += 8

    anomaly = metrics.get("anomaly_score", 0)
    score += anomaly * 20

    return round(min(100, score), 2)


def _fallback_analysis(db: Session, case: RiskCase, merchant: Merchant) -> dict:
    """回退模式：仅输出结构化指标和基础规则建议（V1/V2 兼容）"""
    try:
        metrics = get_all_metrics(db, merchant.id)
        forecast = forecast_cash_gap(db, merchant.id, horizon_days=14)
    except Exception:
        metrics = {}
        forecast = {"predicted_gap": 0, "lowest_cash_day": None, "confidence": 0}

    output = {
        "case_id": f"RC-{case.id:04d}",
        "risk_level": case.risk_level or "medium",
        "case_summary": "Agent 分析失败，已回退到结构化指标模式。请查看原始指标数据。",
        "root_causes": [],
        "cash_gap_forecast": {
            "horizon_days": 14,
            "predicted_gap": forecast.get("predicted_gap", 0),
            "lowest_cash_day": forecast.get("lowest_cash_day"),
            "confidence": forecast.get("confidence", 0),
        },
        "recommendations": [],
        "manual_review_required": True,
    }

    case.agent_output_json = json.dumps(output, ensure_ascii=False)
    case.updated_at = datetime.utcnow()
    db.flush()

    # V2: 回退模式下，高风险案件也触发复核任务生成
    try:
        tasks_generated = generate_tasks_for_case(db, case.id)
        if tasks_generated:
            print(f"✅ 回退模式: 案件 #{case.id} 生成 {len(tasks_generated)} 条执行任务")
    except Exception as task_err:
        print(f"⚠️ 回退模式任务生成失败: {task_err}")

    return output


# ═══════════════════════════════════════════════════════════════
# V3: 多 Agent 编排入口
# ═══════════════════════════════════════════════════════════════

def analyze_v3(db: Session, case_id: int) -> dict:
    """
    V3 分析入口：使用 LangGraph 工作流编排。

    与 V1/V2 的 analyze() 完全兼容：
    - 成功时返回相同的 agent_output 格式
    - 失败时回退到 V1/V2 模式
    """
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        raise ValueError(f"案件 #{case_id} 不存在")

    merchant = db.query(Merchant).filter(Merchant.id == case.merchant_id).first()
    if not merchant:
        raise ValueError(f"商家 #{case.merchant_id} 不存在")

    try:
        from app.workflow.graph import start_workflow

        result = start_workflow(case_id)
        workflow_run_id = result.get("workflow_run_id")
        status = result.get("status", "")

        print(f"✅ V3 工作流完成: run_id={workflow_run_id}, status={status}")

        # 刷新案件数据
        db.expire(case)
        if case.agent_output_json:
            return json.loads(case.agent_output_json)

        # 如果工作流暂停（等待审批），返回中间状态
        if status in ("PAUSED", "PENDING_APPROVAL"):
            return {
                "case_id": f"RC-{case.id:04d}",
                "risk_level": case.risk_level or "medium",
                "case_summary": f"工作流已暂停，等待审批 (workflow_run #{workflow_run_id})",
                "root_causes": [],
                "cash_gap_forecast": {},
                "recommendations": [],
                "manual_review_required": True,
                "workflow_run_id": workflow_run_id,
                "workflow_status": status,
            }

        return result.get("summary", {})

    except ImportError:
        print("⚠️ LangGraph 未安装，回退到 V1/V2 模式")
        return analyze(db, case_id)
    except Exception as e:
        print(f"⚠️ V3 工作流失败，回退到 V1/V2 模式: {e}")
        traceback.print_exc()
        return analyze(db, case_id)
