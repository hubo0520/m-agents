"""
Orchestrator — Agent 编排层

协调指标计算→证据收集→摘要生成→建议生成→守卫校验的完整流程。
"""
import json
import time
import traceback
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Callable, Optional
from sqlalchemy.orm import Session

from app.models.models import (
    RiskCase, Merchant, Recommendation, EvidenceItem,
    FinancingApplication, Claim, ManualReview,
)
from app.engine.metrics import get_all_metrics
from app.engine.cashflow import forecast_cash_gap
from app.agents.evidence_agent import collect_evidence
from app.agents.analysis_agent import generate_summary
from app.agents.recommend_agent import generate_recommendations
from app.agents.guardrail import validate_output
from app.agents.schemas import AgentOutput
from app.services.task_generator import generate_tasks_for_case


# ═══════════════════════════════════════════════════════════════
# 进度事件数据类
# ═══════════════════════════════════════════════════════════════

@dataclass
class AnalysisProgressEvent:
    """分析进度事件"""
    step: str              # 步骤标识，如 "collect_evidence"
    step_name: str         # 步骤中文名，如 "收集证据"
    step_index: int        # 当前步骤索引（从 1 开始）
    total_steps: int       # 总步骤数
    status: str            # "running" | "completed" | "error"
    elapsed_ms: int = 0    # 耗时（毫秒）
    summary: str = ""      # 步骤摘要
    llm_input_summary: str = ""   # LLM 输入摘要（可选）
    llm_output_summary: str = ""  # LLM 输出摘要（可选）

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════
# 数据清理函数
# ═══════════════════════════════════════════════════════════════

def _cleanup_case_data(db: Session, case_id: int):
    """
    重新分析前清理旧数据：
    - evidence_items（该案件的所有证据）
    - recommendations（该案件的所有推荐）
    - 自动生成的任务（financing_applications、claims、manual_reviews 中 case_id 匹配的记录）
    """
    # 1. 清理自动生成的任务（先清任务再清推荐，避免外键问题）
    db.query(FinancingApplication).filter(FinancingApplication.case_id == case_id).delete(synchronize_session=False)
    db.query(Claim).filter(Claim.case_id == case_id).delete(synchronize_session=False)
    db.query(ManualReview).filter(ManualReview.case_id == case_id).delete(synchronize_session=False)

    # 2. 清理推荐
    db.query(Recommendation).filter(Recommendation.case_id == case_id).delete(synchronize_session=False)

    # 3. 清理证据
    db.query(EvidenceItem).filter(EvidenceItem.case_id == case_id).delete(synchronize_session=False)

    db.flush()
    print(f"🗑️ 已清理案件 #{case_id} 的旧分析数据")


# V1/V2 分析步骤定义
V1V2_STEPS = [
    ("compute_metrics", "计算商家指标"),
    ("forecast_gap", "现金缺口预测"),
    ("collect_evidence", "收集证据"),
    ("generate_summary", "生成摘要"),
    ("generate_recommendations", "生成建议"),
    ("guardrail_check", "守卫校验"),
    ("save_results", "保存分析结果"),
]


def _persist_progress(db: Session, case_id: int, event: AnalysisProgressEvent):
    """
    将分析进度持久化到 RiskCase.analysis_progress_json，
    刷新页面后可恢复工作流面板的步骤状态。
    """
    try:
        case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
        if not case:
            return
        # 读取已有进度
        progress = []
        if case.analysis_progress_json:
            progress = json.loads(case.analysis_progress_json)

        # 更新或追加步骤（合并已有数据，保留 LLM 摘要字段不被覆盖）
        found = False
        for i, step_data in enumerate(progress):
            if step_data.get("step") == event.step:
                merged = {**step_data, **event.to_dict()}
                progress[i] = merged
                found = True
                break
        if not found:
            progress.append(event.to_dict())

        case.analysis_progress_json = json.dumps(progress, ensure_ascii=False)
        db.commit()
    except Exception as e:
        print(f"⚠️ 持久化进度失败（不影响分析）: {e}")
        try:
            db.rollback()
        except Exception:
            pass


def _emit_progress(
    on_progress: Optional[Callable[[AnalysisProgressEvent], None]],
    step: str, step_name: str, step_index: int, total_steps: int,
    status: str, elapsed_ms: int = 0, summary: str = "",
    db: Session = None, case_id: int = None,
):
    """安全地发送进度事件，同时持久化到数据库"""
    event = AnalysisProgressEvent(
        step=step, step_name=step_name,
        step_index=step_index, total_steps=total_steps,
        status=status, elapsed_ms=elapsed_ms, summary=summary,
    )
    # 1. 发送回调
    if on_progress:
        try:
            on_progress(event)
        except Exception as e:
            print(f"⚠️ 进度回调失败: {e}")
    # 2. 持久化到数据库
    if db and case_id:
        _persist_progress(db, case_id, event)


def analyze(
    db: Session, case_id: int,
    on_progress: Optional[Callable[[AnalysisProgressEvent], None]] = None,
    on_llm_event=None,
) -> dict:
    """
    对指定案件执行完整分析流程。

    流程:
    1. 计算商家指标
    2. 现金缺口预测
    3. 收集证据
    4. 生成摘要
    5. 生成建议
    6. 守卫校验
    7. 保存到数据库

    异常时回退到"结构化指标 + 规则建议"模式。
    """
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        raise ValueError(f"案件 #{case_id} 不存在")

    merchant = db.query(Merchant).filter(Merchant.id == case.merchant_id).first()
    if not merchant:
        raise ValueError(f"商家 #{case.merchant_id} 不存在")

    total_steps = len(V1V2_STEPS)

    # 重新分析前清理旧数据
    _cleanup_case_data(db, case_id)
    case.status = "ANALYZING"
    case.agent_output_json = None
    case.analysis_progress_json = None  # 清理旧进度
    case.updated_at = datetime.utcnow()
    db.flush()

    try:
        # 1. 计算指标
        _emit_progress(on_progress, "compute_metrics", "计算商家指标", 1, total_steps, "running", db=db, case_id=case_id)
        t0 = time.time()
        metrics = get_all_metrics(db, merchant.id)
        elapsed = int((time.time() - t0) * 1000)
        _emit_progress(on_progress, "compute_metrics", "计算商家指标", 1, total_steps, "completed", elapsed, f"计算了 {len(metrics)} 项指标", db=db, case_id=case_id)

        # 2. 现金缺口预测
        _emit_progress(on_progress, "forecast_gap", "现金缺口预测", 2, total_steps, "running", db=db, case_id=case_id)
        t0 = time.time()
        forecast = forecast_cash_gap(db, merchant.id, horizon_days=14)
        predicted_gap = forecast["predicted_gap"]
        metrics["predicted_gap"] = predicted_gap
        elapsed = int((time.time() - t0) * 1000)
        _emit_progress(on_progress, "forecast_gap", "现金缺口预测", 2, total_steps, "completed", elapsed, f"预测缺口 ¥{predicted_gap:,.0f}", db=db, case_id=case_id)

        # 3. 收集证据
        _emit_progress(on_progress, "collect_evidence", "收集证据", 3, total_steps, "running", db=db, case_id=case_id)
        t0 = time.time()
        evidence = collect_evidence(db, case)
        elapsed = int((time.time() - t0) * 1000)
        ev_count = len(evidence) if isinstance(evidence, list) else 0
        _emit_progress(on_progress, "collect_evidence", "收集证据", 3, total_steps, "completed", elapsed, f"收集到 {ev_count} 条证据", db=db, case_id=case_id)

        # 4. 生成摘要
        _emit_progress(on_progress, "generate_summary", "生成摘要", 4, total_steps, "running", db=db, case_id=case_id)
        t0 = time.time()
        summary = generate_summary(metrics, evidence)
        elapsed = int((time.time() - t0) * 1000)
        _emit_progress(on_progress, "generate_summary", "生成摘要", 4, total_steps, "completed", elapsed, f"风险等级: {summary.get('risk_level', 'unknown')}", db=db, case_id=case_id)

        # 5. 生成建议
        _emit_progress(on_progress, "generate_recommendations", "生成建议", 5, total_steps, "running", db=db, case_id=case_id)
        t0 = time.time()
        recommendations = generate_recommendations(
            db, merchant, metrics, predicted_gap, evidence
        )
        elapsed = int((time.time() - t0) * 1000)
        _emit_progress(on_progress, "generate_recommendations", "生成建议", 5, total_steps, "completed", elapsed, f"生成 {len(recommendations)} 条建议", db=db, case_id=case_id)

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
        _emit_progress(on_progress, "guardrail_check", "守卫校验", 6, total_steps, "running", db=db, case_id=case_id)
        t0 = time.time()
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
        elapsed = int((time.time() - t0) * 1000)
        _emit_progress(on_progress, "guardrail_check", "守卫校验", 6, total_steps, "completed", elapsed, "校验通过" if is_valid else f"校验有问题: {errors}", db=db, case_id=case_id)

        # 8. 保存到数据库
        _emit_progress(on_progress, "save_results", "保存分析结果", 7, total_steps, "running", db=db, case_id=case_id)
        t0 = time.time()
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

        elapsed = int((time.time() - t0) * 1000)
        _emit_progress(on_progress, "save_results", "保存分析结果", 7, total_steps, "completed", elapsed, "分析结果已保存", db=db, case_id=case_id)

        # 分析完成后清理进度数据
        case.analysis_progress_json = None
        db.flush()

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

def analyze_v3(
    db: Session, case_id: int,
    on_progress: Optional[Callable[[AnalysisProgressEvent], None]] = None,
    on_llm_event=None,
) -> dict:
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

    # 重新分析前清理旧数据
    _cleanup_case_data(db, case_id)
    case.status = "ANALYZING"
    case.agent_output_json = None
    case.analysis_progress_json = None  # 清理旧进度
    case.updated_at = datetime.utcnow()
    # ⚠️ 必须 commit 释放 SQLite 写锁，否则 start_workflow 内部创建的
    # 独立 session 会因 "database is locked" 而失败
    db.commit()

    try:
        from app.workflow.graph import start_workflow

        result = start_workflow(case_id, on_progress=on_progress, on_llm_event=on_llm_event)
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
        return analyze(db, case_id, on_progress=on_progress, on_llm_event=on_llm_event)
    except Exception as e:
        print(f"⚠️ V3 工作流失败，回退到 V1/V2 模式: {e}")
        traceback.print_exc()
        return analyze(db, case_id, on_progress=on_progress, on_llm_event=on_llm_event)
