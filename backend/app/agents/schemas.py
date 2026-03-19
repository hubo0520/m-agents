"""
Agent 输出 JSON Schema — Pydantic 模型

V1/V2 原有 schema + V3 Agent 输入输出契约
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


# ═══════════════════════════════════════════════════════════════
# V1/V2 原有 Schema（保持向后兼容）
# ═══════════════════════════════════════════════════════════════

class RootCause(BaseModel):
    label: str
    explanation: str
    confidence: float
    evidence_ids: List[str]


class CashGapForecast(BaseModel):
    horizon_days: int
    predicted_gap: float
    lowest_cash_day: Optional[str] = None
    confidence: float


class ActionRecommendation(BaseModel):
    action_type: str  # advance_settlement / business_loan / insurance_adjust / anomaly_review
    title: str
    why: str
    expected_benefit: str
    confidence: float
    requires_manual_review: bool
    evidence_ids: List[str]


class AgentOutput(BaseModel):
    """V1/V2 兼容输出"""
    case_id: str
    risk_level: str
    case_summary: str
    root_causes: List[RootCause]
    cash_gap_forecast: CashGapForecast
    recommendations: List[ActionRecommendation]
    manual_review_required: bool


# ═══════════════════════════════════════════════════════════════
# V3: Agent 通用输入契约
# ═══════════════════════════════════════════════════════════════

class AgentInput(BaseModel):
    """所有 Agent 通用输入结构"""
    case_id: str = Field(..., description="案件编号，如 RC-2026-0001")
    merchant_id: str = Field(..., description="商家 ID，如 M-1001")
    state_version: int = Field(default=1, description="状态版本号")
    trigger_type: str = Field(default="scheduled_scan", description="触发类型")
    context_refs: List[str] = Field(default_factory=list, description="引用的上下文版本列表")
    policy_version: str = Field(default="policy_default", description="策略版本")


# ═══════════════════════════════════════════════════════════════
# V3: 各 Agent 独立输出 Schema
# ═══════════════════════════════════════════════════════════════

# ────── Triage Agent 输出 ──────

class CaseType(str, Enum):
    CASH_GAP = "cash_gap"
    SUSPECTED_FRAUD = "suspected_fraud"
    BUSINESS_LOAN = "business_loan"
    INSURANCE_CLAIM = "insurance_claim"


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TriageOutput(BaseModel):
    """Triage Agent 输出：案件分类和优先级"""
    case_type: CaseType = Field(..., description="案件类型")
    priority: Priority = Field(..., description="优先级")
    recommended_path: str = Field(..., description="推荐的处理路径")
    reasoning: str = Field(default="", description="分类理由")


# ────── Diagnosis Agent 输出 ──────

class DiagnosisRootCause(BaseModel):
    label: str = Field(..., description="根因标签")
    explanation: str = Field(..., description="根因解释")
    confidence: float = Field(..., ge=0, le=1, description="置信度")
    evidence_ids: List[str] = Field(default_factory=list, description="支撑证据 ID")
    key_factors: Dict[str, Any] = Field(default_factory=dict, description="关键影响因子")


class DiagnosisOutput(BaseModel):
    """Diagnosis Agent 输出：根因分析"""
    root_causes: List[DiagnosisRootCause] = Field(..., description="根因列表")
    business_summary: str = Field(..., description="面向业务的可读摘要")
    key_factors: Dict[str, Any] = Field(default_factory=dict, description="关键影响因子汇总")
    risk_level: str = Field(default="medium", description="风险等级")
    manual_review_required: bool = Field(default=False, description="是否需要人工复核")


# ────── Forecast Agent 输出 ──────

class DailyForecast(BaseModel):
    date: str = Field(..., description="日期 YYYY-MM-DD")
    inflow: float = Field(..., description="预计流入")
    outflow: float = Field(..., description="预计流出")
    netflow: float = Field(..., description="净现金流")


class ForecastOutput(BaseModel):
    """Forecast Agent 输出：现金流预测（纯代码服务，非 LLM）"""
    daily_forecasts: List[DailyForecast] = Field(..., description="逐日预测")
    gap_amount: float = Field(..., description="预测缺口金额")
    min_cash_point: float = Field(..., description="最低现金点")
    confidence_interval: Dict[str, float] = Field(
        default_factory=lambda: {"lower": 0.0, "upper": 0.0},
        description="置信区间"
    )
    horizon_days: int = Field(default=14, description="预测天数")


# ────── Recommendation Agent 输出 ──────

class ExpectedBenefit(BaseModel):
    cash_relief: Optional[float] = None
    time_horizon_days: Optional[int] = None
    description: str = ""


class V3ActionRecommendation(BaseModel):
    """V3 增强版推荐动作"""
    action_type: str = Field(..., description="动作类型")
    title: str = Field(..., description="建议标题")
    why: str = Field(..., description="建议理由")
    expected_benefit: ExpectedBenefit = Field(..., description="预期收益")
    confidence: float = Field(..., ge=0, le=1, description="置信度")
    requires_manual_review: bool = Field(default=True, description="是否需要人工复核")
    evidence_ids: List[str] = Field(default_factory=list, description="支撑证据 ID")


class RecommendationOutput(BaseModel):
    """Recommendation Agent 输出：动作建议"""
    risk_level: str = Field(..., description="风险等级")
    recommendations: List[V3ActionRecommendation] = Field(..., description="建议列表")


# ────── Evidence Agent 输出 ──────

class EvidenceBundle(BaseModel):
    evidence_id: str = Field(..., description="证据 ID")
    evidence_type: str = Field(..., description="证据类型")
    summary: str = Field(..., description="证据摘要")
    source_table: Optional[str] = None
    source_id: Optional[int] = None
    importance_score: float = Field(default=0.5, ge=0, le=1)


class EvidenceOutput(BaseModel):
    """Evidence Agent 输出：证据收集结果"""
    evidence_bundle: List[EvidenceBundle] = Field(..., description="证据包")
    coverage_summary: str = Field(default="", description="证据覆盖摘要")
    total_evidence_count: int = Field(default=0, description="证据总数")


# ────── Guard Agent 输出 ──────

class GuardOutput(BaseModel):
    """Compliance Guard Agent 输出：合规校验结果"""
    passed: bool = Field(..., description="是否通过校验")
    reason_codes: List[str] = Field(default_factory=list, description="原因编码列表")
    blocked_actions: List[str] = Field(default_factory=list, description="被阻断的动作列表")
    next_state: str = Field(default="PENDING_APPROVAL", description="建议的下一状态")
    details: str = Field(default="", description="详细说明")


# ────── Summary Agent 输出 ──────

class ActionResult(BaseModel):
    action_type: str
    status: str  # executed / pending / blocked / failed
    detail: str = ""


class SummaryOutput(BaseModel):
    """Summary Agent 输出：案件最终摘要"""
    case_summary: str = Field(..., description="案件摘要")
    action_results: List[ActionResult] = Field(default_factory=list, description="动作执行结果")
    final_status: str = Field(default="COMPLETED", description="最终状态")
    total_processing_time_ms: Optional[int] = None


# ═══════════════════════════════════════════════════════════════
# V3: LangGraph Workflow State
# ═══════════════════════════════════════════════════════════════

from typing import TypedDict


class WorkflowState(TypedDict, total=False):
    """LangGraph graph state 定义"""
    # 案件基础信息
    case_id: int
    merchant_id: int
    workflow_run_id: int

    # Agent 输入
    agent_input: dict  # AgentInput 序列化

    # 各节点输出
    case_context: dict  # load_case_context 输出
    triage_output: dict  # TriageOutput 序列化
    metrics: dict  # compute_metrics 输出
    forecast_output: dict  # ForecastOutput 序列化
    diagnosis_output: dict  # DiagnosisOutput 序列化
    evidence_output: dict  # EvidenceOutput 序列化
    recommendation_output: dict  # RecommendationOutput 序列化
    guard_output: dict  # GuardOutput 序列化
    summary_output: dict  # SummaryOutput 序列化

    # 审批信息
    approval_task_ids: list  # 创建的审批任务 ID
    approval_results: dict  # 审批结果

    # 执行信息
    execution_results: list  # 执行动作结果
    callback_results: dict  # 外部回调结果

    # 状态控制
    current_status: str  # 当前工作流状态
    error_message: str  # 错误信息
    should_pause: bool  # 是否需要暂停