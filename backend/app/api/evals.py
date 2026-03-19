"""
评测中心 API

离线评测、线上抽样、评测指标计算。
"""
import json
import random
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import EvalDataset, EvalRun, EvalResult, AgentRun


router = APIRouter(prefix="/api/evals", tags=["评测中心"])


# ───────────────── Schema 定义 ─────────────────

class CreateEvalDatasetRequest(BaseModel):
    name: str
    description: str = ""
    test_cases: list  # JSON 数组，每条包含 input 和 expected_output


class CreateEvalRunRequest(BaseModel):
    dataset_id: int
    model_name: str = "gpt-4o"
    prompt_version: str = "1"
    schema_version: str = "1"


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


# ───────────────── POST /api/evals/runs ─────────────────

@router.post("/runs")
def create_eval_run(req: CreateEvalRunRequest, db: Session = Depends(get_db)):
    """启动评测运行"""
    dataset = db.query(EvalDataset).filter(EvalDataset.id == req.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="评测数据集不存在")

    eval_run = EvalRun(
        dataset_id=req.dataset_id,
        model_name=req.model_name,
        prompt_version=req.prompt_version,
        schema_version=req.schema_version,
        status="RUNNING",
    )
    db.add(eval_run)
    db.flush()

    # 逐条执行测试案例
    test_cases = json.loads(dataset.test_cases_json) if dataset.test_cases_json else []
    adopted_count = 0
    hallucination_count = 0
    schema_pass_count = 0
    evidence_covered_count = 0
    total = len(test_cases)

    for i, tc in enumerate(test_cases):
        input_data = tc.get("input", {})
        expected = tc.get("expected_output", {})

        # Mock 评测：实际场景中会调用 Agent 执行
        actual = _mock_eval_execute(input_data, expected)

        # 计算指标
        adopted = _check_adoption(actual, expected)
        has_hallucination = _check_hallucination(actual)
        schema_valid = _check_schema(actual)
        evidence_covered = _check_evidence_coverage(actual)

        if adopted:
            adopted_count += 1
        if has_hallucination:
            hallucination_count += 1
        if schema_valid:
            schema_pass_count += 1
        if evidence_covered:
            evidence_covered_count += 1

        result = EvalResult(
            eval_run_id=eval_run.id,
            test_case_index=i,
            input_json=json.dumps(input_data, ensure_ascii=False),
            expected_output_json=json.dumps(expected, ensure_ascii=False),
            actual_output_json=json.dumps(actual, ensure_ascii=False),
            adopted=1 if adopted else 0,
            has_hallucination=1 if has_hallucination else 0,
            schema_valid=1 if schema_valid else 0,
            evidence_covered=1 if evidence_covered else 0,
        )
        db.add(result)

    # 更新评测指标
    eval_run.adoption_rate = adopted_count / total if total > 0 else 0
    eval_run.rejection_rate = 1 - (adopted_count / total) if total > 0 else 0
    eval_run.evidence_coverage_rate = evidence_covered_count / total if total > 0 else 0
    eval_run.schema_pass_rate = schema_pass_count / total if total > 0 else 0
    eval_run.hallucination_rate = hallucination_count / total if total > 0 else 0
    eval_run.status = "COMPLETED"
    eval_run.ended_at = datetime.utcnow()

    db.commit()
    db.refresh(eval_run)

    return {
        "id": eval_run.id,
        "status": "COMPLETED",
        "adoption_rate": eval_run.adoption_rate,
        "rejection_rate": eval_run.rejection_rate,
        "evidence_coverage_rate": eval_run.evidence_coverage_rate,
        "schema_pass_rate": eval_run.schema_pass_rate,
        "hallucination_rate": eval_run.hallucination_rate,
    }


# ───────────────── GET /api/evals/runs/{eval_run_id} ─────────

@router.get("/runs/{eval_run_id}")
def get_eval_run(eval_run_id: int, db: Session = Depends(get_db)):
    """获取评测运行结果"""
    eval_run = db.query(EvalRun).filter(EvalRun.id == eval_run_id).first()
    if not eval_run:
        raise HTTPException(status_code=404, detail="评测运行不存在")

    results = db.query(EvalResult).filter(EvalResult.eval_run_id == eval_run_id).all()

    return {
        "id": eval_run.id,
        "dataset_id": eval_run.dataset_id,
        "model_name": eval_run.model_name,
        "prompt_version": eval_run.prompt_version,
        "schema_version": eval_run.schema_version,
        "status": eval_run.status,
        "adoption_rate": eval_run.adoption_rate,
        "rejection_rate": eval_run.rejection_rate,
        "evidence_coverage_rate": eval_run.evidence_coverage_rate,
        "schema_pass_rate": eval_run.schema_pass_rate,
        "hallucination_rate": eval_run.hallucination_rate,
        "started_at": str(eval_run.started_at) if eval_run.started_at else None,
        "ended_at": str(eval_run.ended_at) if eval_run.ended_at else None,
        "results": [{
            "test_case_index": r.test_case_index,
            "adopted": r.adopted,
            "has_hallucination": r.has_hallucination,
            "schema_valid": r.schema_valid,
            "evidence_covered": r.evidence_covered,
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
        "adoption_rate": r.adoption_rate,
        "schema_pass_rate": r.schema_pass_rate,
        "hallucination_rate": r.hallucination_rate,
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
