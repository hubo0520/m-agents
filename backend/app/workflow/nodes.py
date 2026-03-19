"""
工作流节点实现

实现 14 个 LangGraph graph 节点函数。
每个节点接收 GraphState，返回 state 增量更新。
"""
import json
import logging
import time
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)

from app.workflow.state import GraphState, WorkflowStatus
from app.core.database import SessionLocal
from app.models.models import (
    RiskCase, Merchant, WorkflowRun, AgentRun, ApprovalTask, AuditLog,
    InsurancePolicy,
)
from app.engine.metrics import get_all_metrics
from app.engine.cashflow import forecast_cash_gap
from app.agents.schemas import AgentInput
from app.agents.triage_agent import run_triage
from app.agents.analysis_agent import run_diagnosis
from app.agents.evidence_agent import run_evidence
from app.agents.compliance_agent import run_compliance_guard
from app.agents.summary_agent import run_summary


def _get_db():
    """获取数据库会话"""
    return SessionLocal()


def _get_model_name() -> str:
    """获取当前实际使用的模型名称"""
    try:
        from app.core.llm_client import is_llm_enabled
        from app.core.config import settings
        if is_llm_enabled():
            return f"llm:{settings.OPENAI_MODEL}"
    except Exception:
        pass
    return "rule-based"


def _record_agent_run(db, workflow_run_id: int, agent_name: str, input_data: dict, output_data: dict, status: str, latency_ms: int):
    """记录 Agent 运行日志"""
    agent_run = AgentRun(
        workflow_run_id=workflow_run_id,
        agent_name=agent_name,
        model_name=_get_model_name(),
        prompt_version="1",
        schema_version="1",
        input_json=json.dumps(input_data, ensure_ascii=False, default=str),
        output_json=json.dumps(output_data, ensure_ascii=False, default=str),
        status=status,
        latency_ms=latency_ms,
    )
    db.add(agent_run)
    db.flush()
    return agent_run


def _update_workflow_run(db, workflow_run_id: int, status: str, current_node: str):
    """更新工作流运行状态"""
    run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_run_id).first()
    if run:
        run.status = status
        run.current_node = current_node
        run.updated_at = datetime.utcnow()
        db.flush()


# ───────────────── 节点 1: load_case_context ─────────────────

def load_case_context(state: GraphState) -> dict:
    """加载案件上下文"""
    db = _get_db()
    try:
        case_id = state["case_id"]
        workflow_run_id = state.get("workflow_run_id")
        start_time = time.time()

        case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
        if not case:
            return {"error_message": f"案件 #{case_id} 不存在", "current_status": WorkflowStatus.FAILED_FINAL.value}

        merchant = db.query(Merchant).filter(Merchant.id == case.merchant_id).first()
        if not merchant:
            return {"error_message": f"商家 #{case.merchant_id} 不存在", "current_status": WorkflowStatus.FAILED_FINAL.value}

        # 检查是否有保单
        has_insurance = db.query(InsurancePolicy).filter(
            InsurancePolicy.merchant_id == merchant.id,
            InsurancePolicy.status == "active",
        ).first() is not None

        # 计算经营天数
        operation_days = (datetime.utcnow() - merchant.created_at).days if merchant.created_at else 0

        context = {
            "case_id": case.id,
            "merchant_id": merchant.id,
            "merchant_name": merchant.name,
            "industry": merchant.industry,
            "store_level": merchant.store_level,
            "settlement_cycle_days": merchant.settlement_cycle_days,
            "operation_days": operation_days,
            "has_insurance": has_insurance,
            "trigger_json": case.trigger_json,
            "risk_level": case.risk_level,
        }

        if workflow_run_id:
            _update_workflow_run(db, workflow_run_id, WorkflowStatus.NEW.value, "load_case_context")
            latency = int((time.time() - start_time) * 1000)
            _record_agent_run(db, workflow_run_id, "load_case_context", {"case_id": case_id}, context, "SUCCESS", latency)

        db.commit()
        return {
            "case_context": context,
            "merchant_id": merchant.id,
            "current_status": WorkflowStatus.NEW.value,
        }
    except Exception as e:
        db.rollback()
        logger.exception("❌ 节点 load_case_context 失败 | case_id=%s", state.get("case_id"))
        return {"error_message": str(e), "current_status": WorkflowStatus.FAILED_RETRYABLE.value}
    finally:
        db.close()


# ───────────────── 节点 2: triage_case ─────────────────

def triage_case(state: GraphState) -> dict:
    """案件分类"""
    db = _get_db()
    try:
        start_time = time.time()
        workflow_run_id = state.get("workflow_run_id")
        context = state.get("case_context", {})
        metrics = state.get("metrics", {})

        agent_input = AgentInput(
            case_id=f"RC-{state['case_id']:04d}",
            merchant_id=f"M-{state['merchant_id']}",
        )

        triage_result = run_triage(agent_input, metrics, context)
        output = triage_result.model_dump()

        if workflow_run_id:
            _update_workflow_run(db, workflow_run_id, WorkflowStatus.TRIAGED.value, "triage_case")
            latency = int((time.time() - start_time) * 1000)
            _record_agent_run(db, workflow_run_id, "triage_agent", {"context": context}, output, "SUCCESS", latency)

        db.commit()
        return {
            "triage_output": output,
            "current_status": WorkflowStatus.TRIAGED.value,
        }
    except Exception as e:
        db.rollback()
        logger.exception("❌ 节点 triage_case 失败 | case_id=%s", state.get("case_id"))
        return {"error_message": str(e), "current_status": WorkflowStatus.FAILED_RETRYABLE.value}
    finally:
        db.close()


# ───────────────── 节点 3: compute_metrics ─────────────────

def compute_metrics(state: GraphState) -> dict:
    """计算商家指标"""
    db = _get_db()
    try:
        start_time = time.time()
        workflow_run_id = state.get("workflow_run_id")
        merchant_id = state["merchant_id"]

        metrics = get_all_metrics(db, merchant_id)

        if workflow_run_id:
            _update_workflow_run(db, workflow_run_id, WorkflowStatus.ANALYZING.value, "compute_metrics")
            latency = int((time.time() - start_time) * 1000)
            _record_agent_run(db, workflow_run_id, "compute_metrics", {"merchant_id": merchant_id}, metrics, "SUCCESS", latency)

        db.commit()
        return {
            "metrics": metrics,
            "current_status": WorkflowStatus.ANALYZING.value,
        }
    except Exception as e:
        db.rollback()
        logger.exception("❌ 节点 compute_metrics 失败 | merchant_id=%s", state.get("merchant_id"))
        return {"error_message": str(e), "current_status": WorkflowStatus.FAILED_RETRYABLE.value}
    finally:
        db.close()


# ───────────────── 节点 4: forecast_gap ─────────────────

def forecast_gap(state: GraphState) -> dict:
    """现金缺口预测"""
    db = _get_db()
    try:
        start_time = time.time()
        workflow_run_id = state.get("workflow_run_id")
        merchant_id = state["merchant_id"]

        forecast = forecast_cash_gap(db, merchant_id, horizon_days=14)
        forecast_output = {
            "daily_forecasts": forecast.get("daily_forecast", []),
            "gap_amount": forecast.get("predicted_gap", 0),
            "min_cash_point": forecast.get("lowest_cash_amount", 0),
            "confidence_interval": {
                "lower": forecast.get("predicted_gap", 0) * 0.8,
                "upper": forecast.get("predicted_gap", 0) * 1.2,
            },
            "horizon_days": 14,
        }

        # 将 predicted_gap 注入 metrics
        metrics = state.get("metrics", {})
        metrics["predicted_gap"] = forecast.get("predicted_gap", 0)

        if workflow_run_id:
            _update_workflow_run(db, workflow_run_id, WorkflowStatus.ANALYZING.value, "forecast_gap")
            latency = int((time.time() - start_time) * 1000)
            _record_agent_run(db, workflow_run_id, "forecast_agent", {"merchant_id": merchant_id}, forecast_output, "SUCCESS", latency)

        db.commit()
        return {
            "forecast_output": forecast_output,
            "metrics": metrics,
        }
    except Exception as e:
        db.rollback()
        logger.exception("❌ 节点 forecast_gap 失败 | merchant_id=%s", state.get("merchant_id"))
        return {"error_message": str(e), "current_status": WorkflowStatus.FAILED_RETRYABLE.value}
    finally:
        db.close()


# ───────────────── 节点 5: diagnose_case ─────────────────

def diagnose_case(state: GraphState) -> dict:
    """根因诊断"""
    db = _get_db()
    try:
        start_time = time.time()
        workflow_run_id = state.get("workflow_run_id")
        case_id = state["case_id"]
        metrics = state.get("metrics", {})

        agent_input = AgentInput(
            case_id=f"RC-{case_id:04d}",
            merchant_id=f"M-{state['merchant_id']}",
        )

        # 获取 evidence 用于分析
        evidence_data = state.get("evidence_output", {})
        evidence_list = []
        for bundle in evidence_data.get("evidence_bundle", []):
            evidence_list.append({
                "evidence_id": bundle.get("evidence_id", ""),
                "type": bundle.get("evidence_type", ""),
                "summary": bundle.get("summary", ""),
            })

        # 从 state 中提取 on_llm_event 回调
        on_llm_event = state.get("_on_llm_event")
        diagnosis = run_diagnosis(agent_input, metrics, evidence_list, on_llm_event=on_llm_event)
        output = diagnosis.model_dump()

        if workflow_run_id:
            _update_workflow_run(db, workflow_run_id, WorkflowStatus.ANALYZING.value, "diagnose_case")
            latency = int((time.time() - start_time) * 1000)
            _record_agent_run(db, workflow_run_id, "diagnosis_agent", {"case_id": case_id}, output, "SUCCESS", latency)

        db.commit()
        return {
            "diagnosis_output": output,
            "current_status": WorkflowStatus.ANALYZING.value,
        }
    except Exception as e:
        db.rollback()
        logger.exception("❌ 节点 diagnose_case 失败 | case_id=%s", state.get("case_id"))
        return {"error_message": str(e), "current_status": WorkflowStatus.FAILED_RETRYABLE.value}
    finally:
        db.close()


# ───────────────── 节点 6: collect_evidence ─────────────────

def collect_evidence(state: GraphState) -> dict:
    """收集证据"""
    db = _get_db()
    try:
        start_time = time.time()
        workflow_run_id = state.get("workflow_run_id")
        case_id = state["case_id"]

        case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
        if not case:
            return {"error_message": f"案件 #{case_id} 不存在"}

        agent_input = AgentInput(
            case_id=f"RC-{case_id:04d}",
            merchant_id=f"M-{state['merchant_id']}",
        )

        evidence = run_evidence(agent_input, db, case)
        output = evidence.model_dump()

        if workflow_run_id:
            _update_workflow_run(db, workflow_run_id, WorkflowStatus.ANALYZING.value, "collect_evidence")
            latency = int((time.time() - start_time) * 1000)
            _record_agent_run(db, workflow_run_id, "evidence_agent", {"case_id": case_id}, output, "SUCCESS", latency)

        db.commit()
        return {
            "evidence_output": output,
        }
    except Exception as e:
        db.rollback()
        logger.exception("❌ 节点 collect_evidence 失败 | case_id=%s", state.get("case_id"))
        return {"error_message": str(e), "current_status": WorkflowStatus.FAILED_RETRYABLE.value}
    finally:
        db.close()


# ───────────────── 节点 7: generate_recommendations ─────────────────

def generate_recommendations(state: GraphState) -> dict:
    """生成建议"""
    db = _get_db()
    try:
        start_time = time.time()
        workflow_run_id = state.get("workflow_run_id")
        case_id = state["case_id"]
        merchant_id = state["merchant_id"]
        metrics = state.get("metrics", {})
        predicted_gap = metrics.get("predicted_gap", 0)

        merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
        agent_input = AgentInput(
            case_id=f"RC-{case_id:04d}",
            merchant_id=f"M-{merchant_id}",
        )

        # 将 evidence_output 中的证据转为旧格式
        evidence_data = state.get("evidence_output", {})
        evidence_list = []
        for bundle in evidence_data.get("evidence_bundle", []):
            evidence_list.append({
                "evidence_id": bundle.get("evidence_id", ""),
                "type": bundle.get("evidence_type", ""),
                "summary": bundle.get("summary", ""),
            })

        from app.agents.recommend_agent import run_recommendations
        on_llm_event = state.get("_on_llm_event")
        rec_output = run_recommendations(agent_input, db, merchant, metrics, predicted_gap, evidence_list, on_llm_event=on_llm_event)
        output = rec_output.model_dump()

        if workflow_run_id:
            _update_workflow_run(db, workflow_run_id, WorkflowStatus.RECOMMENDING.value, "generate_recommendations")
            latency = int((time.time() - start_time) * 1000)
            _record_agent_run(db, workflow_run_id, "recommendation_agent", {"case_id": case_id}, output, "SUCCESS", latency)

        db.commit()
        return {
            "recommendation_output": output,
            "current_status": WorkflowStatus.RECOMMENDING.value,
        }
    except Exception as e:
        db.rollback()
        logger.exception("❌ 节点 generate_recommendations 失败 | case_id=%s", state.get("case_id"))
        return {"error_message": str(e), "current_status": WorkflowStatus.FAILED_RETRYABLE.value}
    finally:
        db.close()


# ───────────────── 节点 8: run_guardrails ─────────────────

def run_guardrails(state: GraphState) -> dict:
    """合规校验"""
    db = _get_db()
    try:
        start_time = time.time()
        workflow_run_id = state.get("workflow_run_id")
        recommendation_output = state.get("recommendation_output", {})
        diagnosis_output = state.get("diagnosis_output", {})
        evidence_output = state.get("evidence_output", {})

        guard_result = run_compliance_guard(
            recommendation_output=recommendation_output,
            diagnosis_output=diagnosis_output,
            evidence_output=evidence_output,
            on_llm_event=state.get("_on_llm_event"),
        )
        output = guard_result.model_dump()

        if workflow_run_id:
            status = WorkflowStatus.BLOCKED_BY_GUARD.value if not guard_result.passed else WorkflowStatus.RECOMMENDING.value
            _update_workflow_run(db, workflow_run_id, status, "run_guardrails")
            latency = int((time.time() - start_time) * 1000)
            _record_agent_run(db, workflow_run_id, "compliance_guard_agent", {}, output, "SUCCESS", latency)

        db.commit()
        return {
            "guard_output": output,
            "current_status": output.get("next_state", WorkflowStatus.PENDING_APPROVAL.value),
        }
    except Exception as e:
        db.rollback()
        logger.exception("❌ 节点 run_guardrails 失败")
        return {"error_message": str(e), "current_status": WorkflowStatus.FAILED_RETRYABLE.value}
    finally:
        db.close()


# ───────────────── 节点 9: create_approval_tasks ─────────────────

def create_approval_tasks(state: GraphState) -> dict:
    """创建审批任务，并将诊断结果和建议持久化到数据库（暂停前最后写入机会）"""
    db = _get_db()
    try:
        start_time = time.time()
        workflow_run_id = state.get("workflow_run_id")
        case_id = state["case_id"]
        recommendation_output = state.get("recommendation_output", {})
        diagnosis_output = state.get("diagnosis_output", {})
        guard_output = state.get("guard_output", {})

        # ──── 1. 持久化 agent_output_json（诊断结果 + 建议） ────
        # finalize_summary 已经在前面执行，这里用完整的 summary_output
        case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
        if case:
            summary_output = state.get("summary_output", {})
            agent_output = {
                "case_id": f"RC-{case_id:04d}",
                "risk_level": diagnosis_output.get("risk_level", "medium"),
                "case_summary": summary_output.get("case_summary", "") or diagnosis_output.get("case_summary", ""),
                "root_causes": diagnosis_output.get("root_causes", []),
                "cash_gap_forecast": state.get("forecast_output", {}),
                "recommendations": recommendation_output.get("recommendations", []),
                "manual_review_required": diagnosis_output.get("manual_review_required", False),
            }
            case.agent_output_json = json.dumps(agent_output, ensure_ascii=False, default=str)
            case.risk_level = diagnosis_output.get("risk_level", case.risk_level)
            case.status = "PENDING_APPROVAL"
            case.updated_at = datetime.utcnow()
            db.flush()

        # ──── 2. 持久化 Recommendation 记录 ────
        from app.models.models import Recommendation
        recs = recommendation_output.get("recommendations", [])
        for rec in recs:
            rec_record = Recommendation(
                case_id=case_id,
                action_type=rec.get("action_type", "unknown"),
                content_json=json.dumps(rec, ensure_ascii=False, default=str),
                confidence=rec.get("confidence", 0),
                requires_manual_review=1 if rec.get("requires_manual_review", True) else 0,
            )
            db.add(rec_record)
        db.flush()

        # ──── 3. 创建审批任务 ────
        approval_task_ids = []
        for rec in recs:
            if rec.get("requires_manual_review", True):
                action_type = rec.get("action_type", "")
                # 映射动作类型到审批类型
                approval_type_map = {
                    "business_loan": "business_loan",
                    "advance_settlement": "advance_settlement",
                    "anomaly_review": "fraud_review",
                    "claim_submission": "claim_submission",
                    "insurance_adjust": "advance_settlement",  # 默认映射
                }
                approval_type = approval_type_map.get(action_type, "fraud_review")

                # 分配审批角色
                role_map = {
                    "business_loan": "finance_ops",
                    "advance_settlement": "finance_ops",
                    "fraud_review": "risk_ops",
                    "claim_submission": "claim_ops",
                }
                assignee_role = role_map.get(approval_type, "risk_ops")

                task = ApprovalTask(
                    workflow_run_id=workflow_run_id,
                    case_id=case_id,
                    approval_type=approval_type,
                    assignee_role=assignee_role,
                    status="PENDING",
                    payload_json=json.dumps(rec, ensure_ascii=False, default=str),
                )
                db.add(task)
                db.flush()
                approval_task_ids.append(task.id)

        if workflow_run_id:
            _update_workflow_run(db, workflow_run_id, WorkflowStatus.PENDING_APPROVAL.value, "create_approval_tasks")
            latency = int((time.time() - start_time) * 1000)
            _record_agent_run(db, workflow_run_id, "create_approval_tasks", {}, {"task_ids": approval_task_ids}, "SUCCESS", latency)

        db.commit()
        return {
            "approval_task_ids": approval_task_ids,
            "current_status": WorkflowStatus.PENDING_APPROVAL.value,
            "should_pause": True,  # 暂停等待审批
        }
    except Exception as e:
        db.rollback()
        logger.exception("❌ 节点 create_approval_tasks 失败 | case_id=%s", state.get("case_id"))
        return {"error_message": str(e), "current_status": WorkflowStatus.FAILED_RETRYABLE.value}
    finally:
        db.close()


# ───────────────── 节点 10: wait_for_approval ─────────────────

def wait_for_approval(state: GraphState) -> dict:
    """等待审批 — 这是一个中断点，通过 LangGraph interrupt 机制暂停"""
    db = _get_db()
    try:
        workflow_run_id = state.get("workflow_run_id")
        if workflow_run_id:
            run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_run_id).first()
            if run:
                run.status = WorkflowStatus.PAUSED.value
                run.current_node = "wait_for_approval"
                run.paused_at = datetime.utcnow()
                db.commit()

        # 检查审批结果（恢复时已有结果）
        approval_results = state.get("approval_results", {})
        if approval_results:
            all_approved = all(r.get("status") == "APPROVED" for r in approval_results.values())
            if all_approved:
                return {
                    "current_status": WorkflowStatus.EXECUTING.value,
                    "should_pause": False,
                }
            else:
                return {
                    "current_status": WorkflowStatus.REJECTED.value,
                    "should_pause": False,
                }

        return {
            "current_status": WorkflowStatus.PAUSED.value,
            "should_pause": True,
        }
    finally:
        db.close()


# ───────────────── 节点 11: execute_actions ─────────────────

def execute_actions(state: GraphState) -> dict:
    """执行审批通过的动作"""
    db = _get_db()
    try:
        start_time = time.time()
        workflow_run_id = state.get("workflow_run_id")
        case_id = state["case_id"]
        merchant_id = state["merchant_id"]
        recommendation_output = state.get("recommendation_output", {})

        from app.agents.execution_agent import run_execution

        # 构建审批通过的动作列表
        approved_actions = []
        for rec in recommendation_output.get("recommendations", []):
            approved_actions.append({
                "action_type": rec.get("action_type", ""),
                "payload": rec,
            })

        results = run_execution(db, case_id, merchant_id, approved_actions, workflow_run_id)
        results_dict = [r.model_dump() for r in results]

        if workflow_run_id:
            _update_workflow_run(db, workflow_run_id, WorkflowStatus.EXECUTING.value, "execute_actions")
            latency = int((time.time() - start_time) * 1000)
            _record_agent_run(db, workflow_run_id, "execution_agent", {}, {"results": results_dict}, "SUCCESS", latency)

        db.commit()
        return {
            "execution_results": results_dict,
            "current_status": WorkflowStatus.EXECUTING.value,
        }
    except Exception as e:
        db.rollback()
        logger.exception("❌ 节点 execute_actions 失败 | case_id=%s", state.get("case_id"))
        return {"error_message": str(e), "current_status": WorkflowStatus.FAILED_RETRYABLE.value}
    finally:
        db.close()


# ───────────────── 节点 12: wait_external_callback ─────────────────

def wait_external_callback(state: GraphState) -> dict:
    """等待外部系统回调 — 目前为占位节点，直接通过"""
    return {
        "callback_results": {"status": "no_callback_needed"},
        "current_status": WorkflowStatus.EXECUTING.value,
    }


# ───────────────── 节点 13: finalize_summary ─────────────────

def finalize_summary(state: GraphState) -> dict:
    """生成最终摘要"""
    db = _get_db()
    try:
        start_time = time.time()
        workflow_run_id = state.get("workflow_run_id")
        case_id = state["case_id"]

        summary = run_summary(
            diagnosis_output=state.get("diagnosis_output", {}),
            recommendation_output=state.get("recommendation_output", {}),
            execution_results=state.get("execution_results"),
            guard_output=state.get("guard_output"),
            on_llm_event=state.get("_on_llm_event"),
        )
        output = summary.model_dump()

        # 更新案件的 agent_output_json（用 summary_agent 生成的完整摘要覆盖）
        case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
        if case:
            case.agent_output_json = json.dumps({
                "case_id": f"RC-{case_id:04d}",
                "risk_level": state.get("diagnosis_output", {}).get("risk_level", "medium"),
                "case_summary": output["case_summary"],
                "root_causes": state.get("diagnosis_output", {}).get("root_causes", []),
                "cash_gap_forecast": state.get("forecast_output", {}),
                "recommendations": state.get("recommendation_output", {}).get("recommendations", []),
                "manual_review_required": state.get("diagnosis_output", {}).get("manual_review_required", False),
            }, ensure_ascii=False, default=str)
            case.risk_level = state.get("diagnosis_output", {}).get("risk_level", case.risk_level)
            # 注意：不设置 case.status = "COMPLETED"，因为后续还有 create_approval_tasks 和 write_audit_log
            case.status = "ANALYZED"
            case.updated_at = datetime.utcnow()

        if workflow_run_id:
            _update_workflow_run(db, workflow_run_id, WorkflowStatus.ANALYZING.value, "finalize_summary")
            latency = int((time.time() - start_time) * 1000)
            _record_agent_run(db, workflow_run_id, "summary_agent", {}, output, "SUCCESS", latency)

        db.commit()
        return {
            "summary_output": output,
            "current_status": WorkflowStatus.COMPLETED.value,
        }
    except Exception as e:
        db.rollback()
        logger.exception("❌ 节点 finalize_summary 失败 | case_id=%s", state.get("case_id"))
        return {"error_message": str(e), "current_status": WorkflowStatus.FAILED_RETRYABLE.value}
    finally:
        db.close()


# ───────────────── 节点 14: write_audit_log ─────────────────

def write_audit_log(state: GraphState) -> dict:
    """写入审计日志"""
    db = _get_db()
    try:
        workflow_run_id = state.get("workflow_run_id")
        case_id = state["case_id"]
        current_status = state.get("current_status", "COMPLETED")

        audit = AuditLog(
            entity_type="workflow_run",
            entity_id=workflow_run_id or 0,
            actor="system",
            action="workflow_completed",
            old_value=None,
            new_value=json.dumps({
                "case_id": case_id,
                "status": current_status,
                "summary": state.get("summary_output", {}).get("case_summary", ""),
            }, ensure_ascii=False),
        )
        db.add(audit)

        # 更新 workflow_run 结束时间
        if workflow_run_id:
            run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_run_id).first()
            if run:
                run.ended_at = datetime.utcnow()
                run.status = current_status

        db.commit()
        return {"current_status": current_status}
    except Exception as e:
        db.rollback()
        return {"error_message": str(e)}
    finally:
        db.close()