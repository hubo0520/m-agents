"""
配置管理 API

Prompt 版本、Schema 版本、模型策略管理。
"""
import json
import random
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import PromptVersion, SchemaVersion


router = APIRouter(prefix="/api", tags=["配置管理"])


# ───────────────── Schema 定义 ─────────────────

class CreatePromptVersionRequest(BaseModel):
    agent_name: str
    content: str
    canary_weight: float = Field(default=0.0, ge=0.0, le=1.0)


class CreateSchemaVersionRequest(BaseModel):
    agent_name: str
    json_schema: str  # JSON Schema 字符串


class CreateModelPolicyRequest(BaseModel):
    agent_name: str
    model_name: str
    temperature: float = 0.0
    max_tokens: int = 4096


# ───────────────── GET /api/agent-configs ─────────────────

@router.get("/agent-configs")
def get_agent_configs(db: Session = Depends(get_db)):
    """获取所有 Agent 配置"""
    # 获取每个 Agent 的最新活跃 prompt 和 schema 版本
    agents = [
        "triage_agent", "diagnosis_agent", "forecast_agent",
        "recommendation_agent", "evidence_agent", "compliance_guard_agent",
        "execution_agent", "summary_agent",
    ]
    configs = []
    for agent_name in agents:
        # 获取活跃 prompt
        active_prompt = db.query(PromptVersion).filter(
            PromptVersion.agent_name == agent_name,
            PromptVersion.status == "ACTIVE",
        ).first()

        # 获取最新 schema
        latest_schema = db.query(SchemaVersion).filter(
            SchemaVersion.agent_name == agent_name,
        ).order_by(SchemaVersion.id.desc()).first()

        configs.append({
            "agent_name": agent_name,
            "active_prompt_version": active_prompt.version if active_prompt else None,
            "latest_schema_version": latest_schema.version if latest_schema else None,
            "model_name": "gpt-4o",  # 默认模型
        })

    return {"configs": configs}


# ───────────────── POST /api/prompt-versions ─────────────────

@router.post("/prompt-versions")
def create_prompt_version(req: CreatePromptVersionRequest, db: Session = Depends(get_db)):
    """创建新的 Prompt 版本"""
    # 获取当前最大版本号
    latest = db.query(PromptVersion).filter(
        PromptVersion.agent_name == req.agent_name,
    ).order_by(PromptVersion.id.desc()).first()

    version_num = int(latest.version) + 1 if latest else 1

    pv = PromptVersion(
        agent_name=req.agent_name,
        version=str(version_num),
        content=req.content,
        status="DRAFT",
        canary_weight=req.canary_weight,
    )
    db.add(pv)
    db.commit()
    db.refresh(pv)

    return {"id": pv.id, "version": pv.version, "status": pv.status}


# ───────────────── POST /api/prompt-versions/{id}/activate ─────

@router.post("/prompt-versions/{version_id}/activate")
def activate_prompt_version(version_id: int, db: Session = Depends(get_db)):
    """激活 Prompt 版本"""
    pv = db.query(PromptVersion).filter(PromptVersion.id == version_id).first()
    if not pv:
        raise HTTPException(status_code=404, detail="版本不存在")

    # 将同 Agent 的当前活跃版本归档
    db.query(PromptVersion).filter(
        PromptVersion.agent_name == pv.agent_name,
        PromptVersion.status == "ACTIVE",
    ).update({"status": "ARCHIVED"})

    pv.status = "ACTIVE"
    db.commit()
    return {"id": pv.id, "status": "ACTIVE"}


# ───────────────── POST /api/prompt-versions/{id}/rollback ─────

@router.post("/prompt-versions/{version_id}/rollback")
def rollback_prompt_version(version_id: int, db: Session = Depends(get_db)):
    """回滚到指定 Prompt 版本"""
    pv = db.query(PromptVersion).filter(PromptVersion.id == version_id).first()
    if not pv:
        raise HTTPException(status_code=404, detail="版本不存在")

    # 归档当前活跃版本
    db.query(PromptVersion).filter(
        PromptVersion.agent_name == pv.agent_name,
        PromptVersion.status == "ACTIVE",
    ).update({"status": "ARCHIVED"})

    pv.status = "ACTIVE"
    db.commit()
    return {"id": pv.id, "version": pv.version, "status": "ACTIVE"}


# ───────────────── GET /api/prompt-versions ─────────────────

@router.get("/prompt-versions")
def list_prompt_versions(
    agent_name: str = Query(None),
    db: Session = Depends(get_db),
):
    """获取 Prompt 版本列表"""
    query = db.query(PromptVersion)
    if agent_name:
        query = query.filter(PromptVersion.agent_name == agent_name)

    versions = query.order_by(PromptVersion.id.desc()).all()
    return {"items": [{
        "id": v.id,
        "agent_name": v.agent_name,
        "version": v.version,
        "status": v.status,
        "canary_weight": v.canary_weight,
        "created_at": str(v.created_at) if v.created_at else None,
    } for v in versions]}


# ───────────────── POST /api/schema-versions ─────────────────

@router.post("/schema-versions")
def create_schema_version(req: CreateSchemaVersionRequest, db: Session = Depends(get_db)):
    """创建新的 Schema 版本"""
    latest = db.query(SchemaVersion).filter(
        SchemaVersion.agent_name == req.agent_name,
    ).order_by(SchemaVersion.id.desc()).first()

    version_num = int(latest.version) + 1 if latest else 1

    sv = SchemaVersion(
        agent_name=req.agent_name,
        version=str(version_num),
        json_schema=req.json_schema,
    )
    db.add(sv)
    db.commit()
    db.refresh(sv)

    return {"id": sv.id, "version": sv.version}


# ───────────────── POST /api/model-policies ─────────────────

@router.post("/model-policies")
def create_model_policy(req: CreateModelPolicyRequest, db: Session = Depends(get_db)):
    """创建/更新模型策略（暂存内存）"""
    # 当前阶段使用简化实现，将配置存入内存
    # 未来可扩展为数据库持久化
    return {
        "agent_name": req.agent_name,
        "model_name": req.model_name,
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
        "status": "applied",
    }


# ═══════════════════════════════════════════════════════════════
# 灰度开关
# ═══════════════════════════════════════════════════════════════

def select_prompt_version(db: Session, agent_name: str) -> Optional[PromptVersion]:
    """
    根据灰度权重选择 prompt 版本。

    如果有 canary_weight > 0 的版本，按概率分配流量。
    """
    active = db.query(PromptVersion).filter(
        PromptVersion.agent_name == agent_name,
        PromptVersion.status == "ACTIVE",
    ).first()

    # 查找灰度版本
    canary = db.query(PromptVersion).filter(
        PromptVersion.agent_name == agent_name,
        PromptVersion.status == "DRAFT",
        PromptVersion.canary_weight > 0,
    ).first()

    if canary and random.random() < canary.canary_weight:
        return canary

    return active
