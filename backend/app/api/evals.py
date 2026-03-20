"""
评测中心 API

真实 Agent 工作流评测、LLM-as-Judge 评分、异步执行。
"""
import json
import time
import random
import traceback
import threading
from datetime import datetime
from app.core.utils import utc_now
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db, SessionLocal
from app.core.config import settings
from app.models.models import EvalDataset, EvalRun, EvalResult, AgentRun, RiskCase

router = APIRouter(prefix="/api/evals", tags=["评测中心"])


# ───────────────── Schema 定义 ─────────────────

class CreateEvalDatasetRequest(BaseModel):
    name: str
    description: str = ""
    test_cases: list  # JSON 数组，每条包含 input 和 expected_output


class UpdateEvalDatasetRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    test_cases: Optional[list] = None


class CreateEvalRunRequest(BaseModel):
    dataset_id: int
    model_name: Optional[str] = None  # 为空时自动使用系统配置的 OPENAI_MODEL
    prompt_version: str = "1"
    schema_version: str = "1"
    reuse_existing: bool = False  # True=复用已有分析结果，False=重新执行工作流


class ImportFromCasesRequest(BaseModel):
    case_ids: List[int]
    dataset_name: str
    description: str = ""


# ═══════════════════════════════════════════════════════════════
# LLM-as-Judge 评测框架
# ═══════════════════════════════════════════════════════════════

# Judge 评分结果的 Pydantic 模型
class JudgeResult(BaseModel):
    """LLM-Judge 结构化评分输出"""
    score: int = Field(..., ge=0, le=100, description="综合评分 0-100")
    reasoning: str = Field(..., description="评分理由，详细说明扣分项")
    risk_level_correct: bool = Field(..., description="风险等级是否与期望一致")
    root_causes_covered: bool = Field(..., description="根因是否覆盖了所有期望的关键根因")
    has_hallucination: bool = Field(..., description="是否存在无证据支撑的虚构内容")


LLM_JUDGE_SYSTEM_PROMPT = """你是一个专业的 AI 评测评委（Judge），负责评估风险分析 Agent 的输出质量。

## 评分维度与权重
1. **诊断正确性**（40%）：风险等级判断是否正确，根因分析是否覆盖关键风险因素
2. **建议合理性**（30%）：推荐的动作是否合理、可执行，是否与风险等级匹配
3. **证据支撑度**（20%）：结论是否有数据和证据支撑，是否存在凭空臆造的数据（幻觉）
4. **输出完整性**（10%）：输出格式是否完整，是否包含必要的字段（risk_level、recommendations、case_summary）

## 评分标准
- 90-100：几乎完美，所有维度表现优秀
- 80-89：良好，有轻微不足
- 60-79：合格，存在明显不足但基本可用
- 40-59：较差，关键维度有明显错误
- 0-39：严重不合格，存在严重错误或大量幻觉

## 输出要求
请以 JSON 格式输出评分结果，严格按照指定的 schema。"""


LLM_JUDGE_USER_PROMPT_TEMPLATE = """请评估以下 Agent 输出的质量：

## 期望输出（参考答案）
```json
{expected_output}
```

## 实际输出（Agent 生成）
```json
{actual_output}
```

请根据评分标准对实际输出进行综合评分，重点关注：
1. 风险等级（risk_level）是否与期望一致
2. 根因分析是否覆盖了期望的关键根因：{expected_root_causes}
3. 推荐的动作类型是否合理
4. 是否存在凭空编造的数据或结论（幻觉）

请输出结构化 JSON 评分结果。"""


class JudgeOutput:
    """run_llm_judge 的返回值，包含评分结果和发送给 LLM 的输入"""
    def __init__(self, result: JudgeResult, judge_input: list):
        self.result = result
        self.judge_input = judge_input  # 发送给 Judge LLM 的完整 messages


async def run_llm_judge(expected_output: dict, actual_output: dict) -> Optional[JudgeOutput]:
    """
    调用 LLM-as-Judge 进行语义级质量评分。

    Args:
        expected_output: 期望的输出（参考答案）
        actual_output: Agent 的实际输出

    Returns:
        JudgeOutput 包含评分结果和 Judge 输入，失败时返回 None
    """
    try:
        from app.core.llm_client import structured_output, is_llm_enabled

        if not is_llm_enabled():
            logger.warning("LLM 未启用，跳过 Judge 评分")
            return None

        expected_root_causes = expected_output.get("expected_root_causes", [])
        user_prompt = LLM_JUDGE_USER_PROMPT_TEMPLATE.format(
            expected_output=json.dumps(expected_output, ensure_ascii=False, indent=2),
            actual_output=json.dumps(actual_output, ensure_ascii=False, indent=2),
            expected_root_causes="、".join(expected_root_causes) if expected_root_causes else "未指定",
        )

        messages = [
            {"role": "system", "content": LLM_JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        result = structured_output(messages, JudgeResult, temperature=0.1)
        return JudgeOutput(result=result, judge_input=messages)

    except Exception as e:
        logger.error("LLM-Judge 评分失败: %s\n%s", e, traceback.format_exc())
        return None


def check_risk_level_match(actual: dict, expected: dict) -> int:
    """规则指标：检查风险等级是否匹配"""
    actual_level = (actual.get("risk_level") or "").lower().strip()
    expected_level = (expected.get("risk_level") or "").lower().strip()
    return 1 if actual_level == expected_level else 0


# ═══════════════════════════════════════════════════════════════
# 真实评测执行引擎
# ═══════════════════════════════════════════════════════════════

def _reuse_existing_result(case_id: int) -> Optional[dict]:
    """
    尝试复用案件已有的分析结果。

    如果案件已分析过（有 agent_output_json），直接返回结果，不重新执行工作流。
    如果案件没有已有结果，返回 None。
    """
    db = SessionLocal()
    try:
        case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
        if not case:
            return None
        if not case.agent_output_json or case.status == "NEW":
            return None  # 没有已有结果，需要重新执行

        agent_output = json.loads(case.agent_output_json)
        return {
            "risk_level": case.risk_level,
            "root_causes": agent_output.get("root_causes", []),
            "recommendations": agent_output.get("recommendations", []),
            "case_summary": agent_output.get("case_summary", ""),
            "evidence_chain": agent_output.get("evidence_chain", []),
            "workflow_status": "REUSED",
        }
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("复用案件 %d 已有结果失败: %s", case_id, e)
        return None
    finally:
        db.close()


def _real_eval_execute(case_id: int) -> dict:
    """
    调用真实 Agent 工作流执行评测（同步函数，在独立线程中运行）。

    Args:
        case_id: 关联的案件 ID

    Returns:
        包含 risk_level、root_causes、recommendations、case_summary 的字典
    """
    from app.workflow.graph import start_workflow

    # 调用真实的 Agent 工作流（无 SSE 回调）
    result = start_workflow(case_id, on_progress=None, on_llm_event=None)

    # 从执行结果提取评测所需的输出
    # start_workflow 会更新 RiskCase 的 agent_output_json
    db = SessionLocal()
    try:
        case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
        if case and case.agent_output_json:
            agent_output = json.loads(case.agent_output_json)
            return {
                "risk_level": case.risk_level,
                "root_causes": agent_output.get("root_causes", []),
                "recommendations": agent_output.get("recommendations", []),
                "case_summary": agent_output.get("case_summary", ""),
                "evidence_chain": agent_output.get("evidence_chain", []),
                "workflow_status": result.get("status", "UNKNOWN"),
            }
        else:
            return {
                "risk_level": case.risk_level if case else "unknown",
                "root_causes": [],
                "recommendations": [],
                "case_summary": "",
                "workflow_status": result.get("status", "UNKNOWN"),
            }
    finally:
        db.close()


def _run_eval_background(eval_run_id: int, dataset_id: int, reuse_existing: bool = False):
    """
    后台线程执行评测运行。

    逐条运行测试用例，执行真实 Agent 工作流 + LLM-Judge 评分。
    在独立线程中运行，不阻塞 FastAPI 事件循环。

    Args:
        eval_run_id: 评测运行 ID
        dataset_id: 数据集 ID
        reuse_existing: 是否复用已有的案件分析结果（True=复用，False=重新执行工作流）
    """
    db = SessionLocal()
    try:
        dataset = db.query(EvalDataset).filter(EvalDataset.id == dataset_id).first()
        if not dataset:
            logger.error("评测数据集 #%d 不存在", dataset_id)
            return

        eval_run = db.query(EvalRun).filter(EvalRun.id == eval_run_id).first()
        if not eval_run:
            logger.error("评测运行 #%d 不存在", eval_run_id)
            return

        test_cases = json.loads(dataset.test_cases_json) if dataset.test_cases_json else []
        total = len(test_cases)
        eval_run.total_count = total
        eval_run.completed_count = 0
        db.commit()

        # 统计聚合变量
        adopted_count = 0
        hallucination_count = 0
        schema_pass_count = 0
        evidence_covered_count = 0
        judge_scores = []
        latencies = []

        for i, tc in enumerate(test_cases):
            input_data = tc.get("input", {})
            expected = tc.get("expected_output", {})
            case_id = input_data.get("case_id")

            actual_output = {}
            latency_ms = 0
            error_msg = None

            # ——— 执行真实 Agent 工作流（或复用已有结果）———
            if case_id:
                reused = False
                if reuse_existing:
                    existing = _reuse_existing_result(case_id)
                    if existing:
                        actual_output = existing
                        latency_ms = 0
                        reused = True
                        logger.info("评测用例 %d 复用已有结果 (case_id=%s)", i, case_id)

                if not reused:
                    try:
                        start_time = time.time()
                        actual_output = _real_eval_execute(case_id)
                        latency_ms = int((time.time() - start_time) * 1000)
                    except Exception as e:
                        error_msg = f"工作流执行失败: {str(e)}"
                        logger.error("评测用例 %d 工作流执行失败 (case_id=%s): %s", i, case_id, e)
                        actual_output = {"error": error_msg}
                        latency_ms = 0
            else:
                error_msg = "测试用例缺少 case_id"
                actual_output = {"error": error_msg}

            # ——— 规则指标计算 ———
            adopted = check_risk_level_match(actual_output, expected) if not error_msg else 0
            has_hallucination = 0
            schema_valid = 1 if ("risk_level" in actual_output and "recommendations" in actual_output) else 0
            evidence_covered = 1 if actual_output.get("evidence_chain") else 0
            risk_level_match = check_risk_level_match(actual_output, expected) if not error_msg else 0
            root_cause_match = 0

            # ——— LLM-Judge 评分 ———
            judge_score_val = None
            judge_reasoning_val = None
            judge_input_json_val = None
            if not error_msg:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 在线程中无法直接 await，使用 asyncio.run 创建新事件循环
                        judge_output = asyncio.run(run_llm_judge(expected, actual_output))
                    else:
                        judge_output = loop.run_until_complete(run_llm_judge(expected, actual_output))
                except RuntimeError:
                    judge_output = asyncio.run(run_llm_judge(expected, actual_output))
                if judge_output:
                    judge_result = judge_output.result
                    judge_input_json_val = json.dumps(judge_output.judge_input, ensure_ascii=False)
                    judge_score_val = judge_result.score
                    judge_reasoning_val = judge_result.reasoning
                    has_hallucination = 1 if judge_result.has_hallucination else 0
                    root_cause_match = 1 if judge_result.root_causes_covered else 0
                    # 用 Judge 结果覆盖规则指标
                    if not judge_result.risk_level_correct:
                        risk_level_match = 0
                    judge_scores.append(judge_result.score)
                else:
                    # Judge 失败降级：仅使用规则指标
                    judge_reasoning_val = "LLM-Judge 评分不可用，仅使用规则指标"

            # ——— 统计聚合 ———
            if adopted:
                adopted_count += 1
            if has_hallucination:
                hallucination_count += 1
            if schema_valid:
                schema_pass_count += 1
            if evidence_covered:
                evidence_covered_count += 1
            if latency_ms > 0:
                latencies.append(latency_ms)

            # ——— 持久化单条结果 ———
            result = EvalResult(
                eval_run_id=eval_run_id,
                test_case_index=i,
                input_json=json.dumps(input_data, ensure_ascii=False),
                expected_output_json=json.dumps(expected, ensure_ascii=False),
                actual_output_json=json.dumps(actual_output, ensure_ascii=False),
                adopted=1 if adopted else 0,
                has_hallucination=1 if has_hallucination else 0,
                schema_valid=1 if schema_valid else 0,
                evidence_covered=1 if evidence_covered else 0,
                judge_score=judge_score_val,
                judge_reasoning=judge_reasoning_val,
                judge_input_json=judge_input_json_val,
                latency_ms=latency_ms,
                risk_level_match=risk_level_match,
                root_cause_match=root_cause_match,
            )
            db.add(result)

            # 更新进度
            eval_run.completed_count = i + 1
            db.commit()

            logger.info("评测用例 %d/%d 完成 | case_id=%s | judge_score=%s | latency=%dms",
                         i + 1, total, case_id, judge_score_val, latency_ms)

        # ——— 完成：计算聚合指标 ———
        eval_run.adoption_rate = adopted_count / total if total > 0 else 0
        eval_run.rejection_rate = 1 - (adopted_count / total) if total > 0 else 0
        eval_run.evidence_coverage_rate = evidence_covered_count / total if total > 0 else 0
        eval_run.schema_pass_rate = schema_pass_count / total if total > 0 else 0
        eval_run.hallucination_rate = hallucination_count / total if total > 0 else 0
        eval_run.avg_judge_score = sum(judge_scores) / len(judge_scores) if judge_scores else None
        eval_run.avg_latency_ms = int(sum(latencies) / len(latencies)) if latencies else None
        eval_run.status = "COMPLETED"
        eval_run.ended_at = utc_now()
        db.commit()

        logger.info("评测运行 #%d 完成 | %d/%d 用例 | avg_judge=%.1f",
                     eval_run_id, total, total,
                     eval_run.avg_judge_score or 0)

    except Exception as e:
        logger.exception("评测运行 #%d 异常终止", eval_run_id)
        try:
            eval_run = db.query(EvalRun).filter(EvalRun.id == eval_run_id).first()
            if eval_run:
                eval_run.status = "FAILED"
                eval_run.ended_at = utc_now()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════
# API 端点
# ═══════════════════════════════════════════════════════════════

# ───────────────── POST /api/evals/datasets ─────────────────

@router.post("/datasets")
def create_eval_dataset(req: CreateEvalDatasetRequest, db: Session = Depends(get_db)):
    """创建评测数据集"""
    dataset = EvalDataset(
        name=req.name,
        description=req.description,
        test_cases_json=json.dumps(req.test_cases, ensure_ascii=False),
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return {
        "id": dataset.id,
        "name": dataset.name,
        "test_case_count": len(req.test_cases),
    }


# ───────────────── GET /api/evals/datasets ─────────────────

@router.get("/datasets")
def list_eval_datasets(db: Session = Depends(get_db)):
    """获取评测数据集列表"""
    datasets = db.query(EvalDataset).order_by(EvalDataset.id.desc()).all()
    return {"items": [{
        "id": d.id,
        "name": d.name,
        "description": d.description,
        "test_case_count": len(json.loads(d.test_cases_json)) if d.test_cases_json else 0,
        "created_at": str(d.created_at) if d.created_at else None,
    } for d in datasets]}


# ───────────────── GET /api/evals/datasets/{id} ─────────────────

@router.get("/datasets/{dataset_id}")
def get_eval_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """获取数据集详情（含测试用例）"""
    dataset = db.query(EvalDataset).filter(EvalDataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="评测数据集不存在")

    test_cases = json.loads(dataset.test_cases_json) if dataset.test_cases_json else []
    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "test_cases": test_cases,
        "test_case_count": len(test_cases),
        "created_at": str(dataset.created_at) if dataset.created_at else None,
    }


# ───────────────── PUT /api/evals/datasets/{id} ─────────────────

@router.put("/datasets/{dataset_id}")
def update_eval_dataset(dataset_id: int, req: UpdateEvalDatasetRequest, db: Session = Depends(get_db)):
    """编辑数据集的测试用例内容"""
    dataset = db.query(EvalDataset).filter(EvalDataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="评测数据集不存在")

    if req.name is not None:
        dataset.name = req.name
    if req.description is not None:
        dataset.description = req.description
    if req.test_cases is not None:
        dataset.test_cases_json = json.dumps(req.test_cases, ensure_ascii=False)

    db.commit()
    db.refresh(dataset)

    test_cases = json.loads(dataset.test_cases_json) if dataset.test_cases_json else []
    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "test_case_count": len(test_cases),
    }


# ───────────────── POST /api/evals/datasets/import-from-cases ─────

@router.post("/datasets/import-from-cases")
def import_from_cases(req: ImportFromCasesRequest, db: Session = Depends(get_db)):
    """从线上已分析案件导入为测试用例"""
    test_cases = []
    for cid in req.case_ids:
        case = db.query(RiskCase).filter(RiskCase.id == cid).first()
        if not case:
            continue
        if case.status == "NEW":
            continue  # 跳过未分析的案件

        # 从 agent_output_json 提取期望输出
        expected_output = {"risk_level": case.risk_level}
        if case.agent_output_json:
            try:
                agent_out = json.loads(case.agent_output_json)
                root_causes = agent_out.get("root_causes", [])
                if isinstance(root_causes, list):
                    expected_output["expected_root_causes"] = [
                        rc.get("cause", rc) if isinstance(rc, dict) else str(rc)
                        for rc in root_causes
                    ]
                recs = agent_out.get("recommendations", [])
                if isinstance(recs, list):
                    expected_output["expected_action_types"] = [
                        r.get("action_type", "") if isinstance(r, dict) else ""
                        for r in recs
                    ]
            except (json.JSONDecodeError, AttributeError):
                pass

        test_cases.append({
            "input": {"case_id": cid},
            "expected_output": expected_output,
        })

    if not test_cases:
        raise HTTPException(status_code=400, detail="没有可导入的有效案件")

    dataset = EvalDataset(
        name=req.dataset_name,
        description=req.description,
        test_cases_json=json.dumps(test_cases, ensure_ascii=False),
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return {
        "id": dataset.id,
        "name": dataset.name,
        "test_case_count": len(test_cases),
        "imported_case_ids": [tc["input"]["case_id"] for tc in test_cases],
    }


# ───────────────── POST /api/evals/runs（异步） ─────────────────

@router.post("/runs")
async def create_eval_run(
    req: CreateEvalRunRequest,
    db: Session = Depends(get_db),
):
    """启动评测运行（异步执行）"""
    dataset = db.query(EvalDataset).filter(EvalDataset.id == req.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="评测数据集不存在")

    test_cases = json.loads(dataset.test_cases_json) if dataset.test_cases_json else []

    # 如果未指定模型名，使用系统配置的 OPENAI_MODEL
    actual_model_name = req.model_name or settings.OPENAI_MODEL

    eval_run = EvalRun(
        dataset_id=req.dataset_id,
        model_name=actual_model_name,
        prompt_version=req.prompt_version,
        schema_version=req.schema_version,
        status="RUNNING",
        total_count=len(test_cases),
        completed_count=0,
    )
    db.add(eval_run)
    db.commit()
    db.refresh(eval_run)

    # 在独立线程中启动评测任务，避免阻塞事件循环
    eval_thread = threading.Thread(
        target=_run_eval_background,
        args=(eval_run.id, req.dataset_id, req.reuse_existing),
        name=f"eval-run-{eval_run.id}",
        daemon=True,
    )
    eval_thread.start()

    return {
        "id": eval_run.id,
        "status": "RUNNING",
        "total_count": len(test_cases),
        "completed_count": 0,
    }


# ───────────────── GET /api/evals/runs/{eval_run_id} ─────────

@router.get("/runs/{eval_run_id}")
def get_eval_run(eval_run_id: int, db: Session = Depends(get_db)):
    """获取评测运行详情（含进度和结果）"""
    eval_run = db.query(EvalRun).filter(EvalRun.id == eval_run_id).first()
    if not eval_run:
        raise HTTPException(status_code=404, detail="评测运行不存在")

    results = db.query(EvalResult).filter(
        EvalResult.eval_run_id == eval_run_id
    ).order_by(EvalResult.test_case_index).all()

    return {
        "id": eval_run.id,
        "dataset_id": eval_run.dataset_id,
        "model_name": eval_run.model_name,
        "prompt_version": eval_run.prompt_version,
        "schema_version": eval_run.schema_version,
        "status": eval_run.status,
        "completed_count": eval_run.completed_count or 0,
        "total_count": eval_run.total_count or 0,
        "adoption_rate": eval_run.adoption_rate,
        "rejection_rate": eval_run.rejection_rate,
        "evidence_coverage_rate": eval_run.evidence_coverage_rate,
        "schema_pass_rate": eval_run.schema_pass_rate,
        "hallucination_rate": eval_run.hallucination_rate,
        "avg_judge_score": eval_run.avg_judge_score,
        "avg_latency_ms": eval_run.avg_latency_ms,
        "started_at": str(eval_run.started_at) if eval_run.started_at else None,
        "ended_at": str(eval_run.ended_at) if eval_run.ended_at else None,
        "results": [{
            "test_case_index": r.test_case_index,
            "input_json": r.input_json,
            "expected_output_json": r.expected_output_json,
            "actual_output_json": r.actual_output_json,
            "adopted": r.adopted,
            "has_hallucination": r.has_hallucination,
            "schema_valid": r.schema_valid,
            "evidence_covered": r.evidence_covered,
            "judge_score": r.judge_score,
            "judge_reasoning": r.judge_reasoning,
            "judge_input_json": r.judge_input_json,
            "latency_ms": r.latency_ms,
            "risk_level_match": r.risk_level_match,
            "root_cause_match": r.root_cause_match,
        } for r in results],
    }


# ───────────────── GET /api/evals/runs ─────────────────

@router.get("/runs")
def list_eval_runs(db: Session = Depends(get_db)):
    """获取评测运行列表"""
    runs = db.query(EvalRun).order_by(EvalRun.id.desc()).all()
    return {"items": [{
        "id": r.id,
        "dataset_id": r.dataset_id,
        "model_name": r.model_name,
        "status": r.status,
        "completed_count": r.completed_count or 0,
        "total_count": r.total_count or 0,
        "adoption_rate": r.adoption_rate,
        "schema_pass_rate": r.schema_pass_rate,
        "hallucination_rate": r.hallucination_rate,
        "avg_judge_score": r.avg_judge_score,
        "avg_latency_ms": r.avg_latency_ms,
        "started_at": str(r.started_at) if r.started_at else None,
        "ended_at": str(r.ended_at) if r.ended_at else None,
    } for r in runs]}


# ───────────────── 线上抽样 ─────────────────

@router.get("/sampling")
def online_sampling(
    agent_name: str = Query(..., description="Agent 名称"),
    sample_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """从线上 agent_runs 中随机抽样"""
    runs = db.query(AgentRun).filter(
        AgentRun.agent_name == agent_name,
        AgentRun.status == "SUCCESS",
    ).order_by(AgentRun.created_at.desc()).limit(100).all()

    if len(runs) <= sample_size:
        sampled = runs
    else:
        sampled = random.sample(runs, sample_size)

    return {"items": [{
        "id": r.id,
        "workflow_run_id": r.workflow_run_id,
        "agent_name": r.agent_name,
        "model_name": r.model_name,
        "output_json": r.output_json,
        "latency_ms": r.latency_ms,
        "created_at": str(r.created_at) if r.created_at else None,
    } for r in sampled]}


# ═══════════════════════════════════════════════════════════════
# 评测辅助函数
# ═══════════════════════════════════════════════════════════════

def _mock_eval_execute(input_data: dict, expected: dict) -> dict:
    """Mock 评测执行"""
    # 模拟 Agent 输出（实际场景中调用真实 Agent）
    return {
        "risk_level": expected.get("risk_level", "medium"),
        "recommendations": expected.get("recommendations", []),
        "evidence_ids": expected.get("evidence_ids", ["EV-001"]),
    }


def _check_adoption(actual: dict, expected: dict) -> bool:
    """检查采纳率：实际输出是否与期望匹配"""
    return actual.get("risk_level") == expected.get("risk_level")


def _check_hallucination(actual: dict) -> bool:
    """检查幻觉：输出是否有 evidence_ids 支撑"""
    evidence_ids = actual.get("evidence_ids", [])
    return len(evidence_ids) == 0  # 没有证据则视为幻觉


def _check_schema(actual: dict) -> bool:
    """检查 schema 合格率"""
    # 简化检查：确保关键字段存在
    return "risk_level" in actual


def _check_evidence_coverage(actual: dict) -> bool:
    """检查证据覆盖率"""
    recommendations = actual.get("recommendations", [])
    if not recommendations:
        return True
    for rec in recommendations:
        if isinstance(rec, dict) and not rec.get("evidence_ids"):
            return False
    return True
