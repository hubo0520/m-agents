"""
工作流状态定义

定义 LangGraph graph state 和工作流状态枚举。
"""
from typing import TypedDict, Optional, List, Dict, Any
from enum import Enum


class WorkflowStatus(str, Enum):
    """工作流运行状态"""
    NEW = "NEW"
    TRIAGED = "TRIAGED"
    ANALYZING = "ANALYZING"
    RECOMMENDING = "RECOMMENDING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    EXECUTING = "EXECUTING"
    WAITING_CALLBACK = "WAITING_CALLBACK"
    COMPLETED = "COMPLETED"
    # 异常分支
    NEEDS_MORE_DATA = "NEEDS_MORE_DATA"
    BLOCKED_BY_GUARD = "BLOCKED_BY_GUARD"
    REJECTED = "REJECTED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_FINAL = "FAILED_FINAL"
    PAUSED = "PAUSED"
    RESUMED = "RESUMED"


class GraphState(TypedDict, total=False):
    """LangGraph graph state 定义 — 在节点间传递的共享状态"""
    # 案件基础信息
    case_id: int
    merchant_id: int
    workflow_run_id: int

    # Agent 输入
    agent_input: dict

    # 各节点输出
    case_context: dict
    triage_output: dict
    metrics: dict
    forecast_output: dict
    diagnosis_output: dict
    evidence_output: dict
    recommendation_output: dict
    guard_output: dict
    summary_output: dict

    # 审批信息
    approval_task_ids: list
    approval_results: dict

    # 执行信息
    execution_results: list
    callback_results: dict

    # 状态控制
    current_status: str
    error_message: str
    should_pause: bool
