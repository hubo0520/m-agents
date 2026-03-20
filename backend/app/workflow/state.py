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

    # Agent 间累积式上下文传递
    analysis_context: str


def append_analysis_context(
    state: GraphState,
    agent_name: str,
    insight: str,
    max_per_agent: int = 200,
    max_total: int = 1500,
) -> str:
    """
    向 analysis_context 追加 Agent 洞察。

    Args:
        state: 当前 GraphState
        agent_name: Agent 名称标签
        insight: 需要追加的洞察文本
        max_per_agent: 每个 Agent 追加内容的字符上限
        max_total: analysis_context 总字符上限

    Returns:
        更新后的 analysis_context 字符串
    """
    # 截断单条洞察
    if len(insight) > max_per_agent:
        insight = insight[:max_per_agent]

    entry = f"[{agent_name}] {insight}"
    current = state.get("analysis_context", "") or ""

    # 追加新条目
    if current:
        new_context = f"{current}\n{entry}"
    else:
        new_context = entry

    # 如果超出总长度限制，截断最早的条目
    while len(new_context) > max_total and "\n" in new_context:
        # 移除最早的一行
        new_context = new_context[new_context.index("\n") + 1:]

    # 极端情况：单条就超限
    if len(new_context) > max_total:
        new_context = new_context[:max_total]

    return new_context
