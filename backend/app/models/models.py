"""数据库模型 — V1/V2 核心业务表 + V3 多 Agent 生产化表"""
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, Date, Boolean,
    ForeignKey, Index, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


# ─────────────────────── 枚举 ───────────────────────

class CaseStatus(str, enum.Enum):
    NEW = "NEW"
    ANALYZED = "ANALYZED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RiskLevel(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReviewDecision(str, enum.Enum):
    APPROVE = "approve"
    APPROVE_WITH_CHANGES = "approve_with_changes"
    REJECT = "reject"


class TaskStatus(str, enum.Enum):
    """融资申请 / 理赔申请的状态"""
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"


class ReviewTaskStatus(str, enum.Enum):
    """人工复核任务的状态"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"


# ─────────────────────── V3 枚举 ───────────────────────

class WorkflowStatus(str, enum.Enum):
    """工作流运行状态"""
    NEW = "NEW"
    TRIAGED = "TRIAGED"
    ANALYZING = "ANALYZING"
    RECOMMENDING = "RECOMMENDING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    EXECUTING = "EXECUTING"
    WAITING_CALLBACK = "WAITING_CALLBACK"
    COMPLETED = "COMPLETED"
    NEEDS_MORE_DATA = "NEEDS_MORE_DATA"
    BLOCKED_BY_GUARD = "BLOCKED_BY_GUARD"
    REJECTED = "REJECTED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_FINAL = "FAILED_FINAL"
    PAUSED = "PAUSED"
    RESUMED = "RESUMED"


class ApprovalType(str, enum.Enum):
    """审批类型"""
    BUSINESS_LOAN = "business_loan"
    ADVANCE_SETTLEMENT = "advance_settlement"
    FRAUD_REVIEW = "fraud_review"
    CLAIM_SUBMISSION = "claim_submission"


class ApprovalStatus(str, enum.Enum):
    """审批状态"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    OVERDUE = "OVERDUE"


class AgentRunStatus(str, enum.Enum):
    """Agent 运行状态"""
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ToolInvocationStatus(str, enum.Enum):
    """工具调用状态"""
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class PromptVersionStatus(str, enum.Enum):
    """Prompt 版本状态"""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


# ─────────────────────── 0. users (认证) ───────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    display_name = Column(String(128), nullable=False)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(32), nullable=False, default="risk_ops")  # 对应 Role 枚举
    is_active = Column(Boolean, nullable=False, default=True)
    is_superadmin = Column(Boolean, nullable=False, default=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─────────────────────── 1. merchants ───────────────────────

class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    industry = Column(String(64), nullable=False)
    settlement_cycle_days = Column(Integer, nullable=False, default=7)
    store_level = Column(String(16), nullable=False, default="silver")  # gold/silver/bronze
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联
    orders = relationship("Order", back_populates="merchant")
    settlements = relationship("Settlement", back_populates="merchant")
    insurance_policies = relationship("InsurancePolicy", back_populates="merchant")
    risk_cases = relationship("RiskCase", back_populates="merchant")


# ─────────────────────── 2. orders ───────────────────────

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    sku_id = Column(String(64), nullable=True)
    order_amount = Column(Float, nullable=False)
    order_time = Column(DateTime, nullable=False)
    delivered_time = Column(DateTime, nullable=True)

    merchant = relationship("Merchant", back_populates="orders")
    returns = relationship("Return", back_populates="order")
    logistics_events = relationship("LogisticsEvent", back_populates="order")


# ─────────────────────── 3. returns ───────────────────────

class Return(Base):
    __tablename__ = "returns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    return_reason = Column(String(128), nullable=True)
    return_time = Column(DateTime, nullable=False)
    refund_amount = Column(Float, nullable=False)
    status = Column(String(32), nullable=False, default="completed")  # pending/completed/rejected

    order = relationship("Order", back_populates="returns")


# ─────────────────────── 4. logistics_events ───────────────────────

class LogisticsEvent(Base):
    __tablename__ = "logistics_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    event_type = Column(String(32), nullable=False)  # picked_up/in_transit/delivered/returned
    event_time = Column(DateTime, nullable=False)

    order = relationship("Order", back_populates="logistics_events")


# ─────────────────────── 5. settlements ───────────────────────

class Settlement(Base):
    __tablename__ = "settlements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    expected_settlement_date = Column(Date, nullable=False)
    actual_settlement_date = Column(Date, nullable=True)
    amount = Column(Float, nullable=False)
    status = Column(String(32), nullable=False, default="pending")  # pending/settled/delayed

    merchant = relationship("Merchant", back_populates="settlements")


# ─────────────────────── 6. insurance_policies ───────────────────────

class InsurancePolicy(Base):
    __tablename__ = "insurance_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    policy_type = Column(String(64), nullable=False)  # shipping_return/freight
    coverage_limit = Column(Float, nullable=False)
    premium_rate = Column(Float, nullable=False)
    status = Column(String(32), nullable=False, default="active")

    merchant = relationship("Merchant", back_populates="insurance_policies")


# ─────────────────────── 7. financing_products ───────────────────────

class FinancingProduct(Base):
    __tablename__ = "financing_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    max_amount = Column(Float, nullable=False)
    eligibility_rule_json = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="active")


# ─────────────────────── 8. risk_cases ───────────────────────

class RiskCase(Base):
    __tablename__ = "risk_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    risk_score = Column(Float, nullable=True)
    risk_level = Column(String(16), nullable=False, default="low")
    trigger_json = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="NEW")
    agent_output_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="risk_cases")
    evidence_items = relationship("EvidenceItem", back_populates="risk_case")
    recommendations = relationship("Recommendation", back_populates="risk_case")
    reviews = relationship("Review", back_populates="risk_case")
    financing_applications = relationship("FinancingApplication", back_populates="risk_case")
    claims = relationship("Claim", back_populates="risk_case")
    manual_reviews = relationship("ManualReview", back_populates="risk_case")

    __table_args__ = (
        Index("ix_risk_cases_merchant_id", "merchant_id"),
        Index("ix_risk_cases_status", "status"),
        Index("ix_risk_cases_risk_level", "risk_level"),
    )


# ─────────────────────── 9. evidence_items ───────────────────────

class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("risk_cases.id"), nullable=False)
    evidence_type = Column(String(64), nullable=False)  # order/return/logistics/settlement/rule_hit/product_match
    source_table = Column(String(64), nullable=True)
    source_id = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
    importance_score = Column(Float, nullable=True)

    risk_case = relationship("RiskCase", back_populates="evidence_items")


# ─────────────────────── 10. recommendations ───────────────────────

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("risk_cases.id"), nullable=False)
    action_type = Column(String(64), nullable=False)
    content_json = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    requires_manual_review = Column(Integer, nullable=False, default=0)  # 0=false, 1=true
    task_generated = Column(Integer, nullable=False, default=0)  # 0=未生成, 1=已生成
    task_type = Column(String(64), nullable=True)  # financing / claim / manual_review
    task_id = Column(Integer, nullable=True)

    risk_case = relationship("RiskCase", back_populates="recommendations")


# ─────────────────────── 11. reviews ───────────────────────

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("risk_cases.id"), nullable=False)
    reviewer_id = Column(String(64), nullable=True)
    decision = Column(String(32), nullable=False)
    comment = Column(Text, nullable=True)
    final_action_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    risk_case = relationship("RiskCase", back_populates="reviews")


# ─────────────────────── 12. audit_logs ───────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(64), nullable=False)  # risk_case/recommendation/review/financing_application/claim/manual_review
    entity_id = Column(Integer, nullable=False)
    actor = Column(String(64), nullable=True)
    action = Column(String(64), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─────────────────────── 13. financing_applications ───────────────────────

class FinancingApplication(Base):
    __tablename__ = "financing_applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    case_id = Column(Integer, ForeignKey("risk_cases.id"), nullable=False)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=True)
    amount_requested = Column(Float, nullable=False)
    loan_purpose = Column(String(256), nullable=True)
    repayment_plan_json = Column(Text, nullable=True)
    merchant_info_snapshot_json = Column(Text, nullable=True)
    historical_settlement_json = Column(Text, nullable=True)
    approval_status = Column(String(32), nullable=False, default="DRAFT")
    reviewer_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    risk_case = relationship("RiskCase", back_populates="financing_applications")

    __table_args__ = (
        Index("ix_financing_applications_case_id", "case_id"),
        Index("ix_financing_applications_status", "approval_status"),
    )


# ─────────────────────── 14. claims ───────────────────────

class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    case_id = Column(Integer, ForeignKey("risk_cases.id"), nullable=False)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=True)
    policy_id = Column(Integer, ForeignKey("insurance_policies.id"), nullable=True)
    claim_amount = Column(Float, nullable=False)
    claim_reason = Column(String(256), nullable=True)
    evidence_snapshot_json = Column(Text, nullable=True)
    return_details_json = Column(Text, nullable=True)
    claim_status = Column(String(32), nullable=False, default="DRAFT")
    reviewer_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    risk_case = relationship("RiskCase", back_populates="claims")

    __table_args__ = (
        Index("ix_claims_case_id", "case_id"),
        Index("ix_claims_status", "claim_status"),
    )


# ─────────────────────── 15. manual_reviews ───────────────────────

class ManualReview(Base):
    __tablename__ = "manual_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    case_id = Column(Integer, ForeignKey("risk_cases.id"), nullable=False)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=True)
    task_type = Column(String(64), nullable=False)  # return_fraud / high_risk_mandatory / anomaly_review
    review_reason = Column(Text, nullable=True)
    evidence_ids_json = Column(Text, nullable=True)
    assigned_to = Column(String(64), nullable=True, default="unassigned")
    status = Column(String(32), nullable=False, default="PENDING")
    review_result = Column(String(64), nullable=True)
    reviewer_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    risk_case = relationship("RiskCase", back_populates="manual_reviews")

    __table_args__ = (
        Index("ix_manual_reviews_case_id", "case_id"),
        Index("ix_manual_reviews_status", "status"),
    )


# ═══════════════════════════════════════════════════════════════
# V3: 多 Agent 生产化表
# ═══════════════════════════════════════════════════════════════

# ─────────────────────── 16. workflow_runs ───────────────────────

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("risk_cases.id"), nullable=False)
    graph_version = Column(String(64), nullable=False, default="v3.0")
    status = Column(String(32), nullable=False, default="NEW")
    current_node = Column(String(128), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paused_at = Column(DateTime, nullable=True)
    resumed_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)

    agent_runs = relationship("AgentRun", back_populates="workflow_run")
    checkpoints = relationship("Checkpoint", back_populates="workflow_run")
    approval_tasks = relationship("ApprovalTask", back_populates="workflow_run")
    tool_invocations = relationship("ToolInvocation", back_populates="workflow_run")

    __table_args__ = (
        Index("ix_workflow_runs_case_id", "case_id"),
        Index("ix_workflow_runs_status", "status"),
    )


# ─────────────────────── 17. agent_runs ───────────────────────

class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id"), nullable=False)
    agent_name = Column(String(64), nullable=False)
    model_name = Column(String(64), nullable=True)
    prompt_version = Column(String(16), nullable=True)
    schema_version = Column(String(16), nullable=True)
    input_json = Column(Text, nullable=True)
    output_json = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="RUNNING")
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    workflow_run = relationship("WorkflowRun", back_populates="agent_runs")

    __table_args__ = (
        Index("ix_agent_runs_workflow_run_id", "workflow_run_id"),
        Index("ix_agent_runs_agent_name", "agent_name"),
    )


# ─────────────────────── 18. checkpoints ───────────────────────

class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id"), nullable=False)
    node_name = Column(String(128), nullable=False)
    checkpoint_blob = Column(Text, nullable=True)  # JSON 序列化的 checkpoint 数据
    created_at = Column(DateTime, default=datetime.utcnow)

    workflow_run = relationship("WorkflowRun", back_populates="checkpoints")


# ─────────────────────── 19. approval_tasks ───────────────────────

class ApprovalTask(Base):
    __tablename__ = "approval_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id"), nullable=True)
    case_id = Column(Integer, ForeignKey("risk_cases.id"), nullable=False)
    approval_type = Column(String(64), nullable=False)
    assignee_role = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="PENDING")
    payload_json = Column(Text, nullable=True)  # 审批内容
    reviewer = Column(String(64), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    comment = Column(Text, nullable=True)
    final_action_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    due_at = Column(DateTime, nullable=True)

    workflow_run = relationship("WorkflowRun", back_populates="approval_tasks")

    __table_args__ = (
        Index("ix_approval_tasks_case_id", "case_id"),
        Index("ix_approval_tasks_status", "status"),
        Index("ix_approval_tasks_workflow_run_id", "workflow_run_id"),
    )


# ─────────────────────── 20. tool_invocations ───────────────────────

class ToolInvocation(Base):
    __tablename__ = "tool_invocations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id"), nullable=True)
    tool_name = Column(String(128), nullable=False)
    tool_version = Column(String(32), nullable=True)
    input_json = Column(Text, nullable=True)
    output_json = Column(Text, nullable=True)
    approval_required = Column(Integer, nullable=False, default=0)  # 0=否, 1=是
    approval_status = Column(String(32), nullable=True)
    status = Column(String(32), nullable=False, default="PENDING")
    idempotency_key = Column(String(256), nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    workflow_run = relationship("WorkflowRun", back_populates="tool_invocations")

    __table_args__ = (
        Index("ix_tool_invocations_workflow_run_id", "workflow_run_id"),
        Index("ix_tool_invocations_tool_name", "tool_name"),
    )


# ─────────────────────── 21. prompt_versions ───────────────────────

class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(64), nullable=False)
    version = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="DRAFT")
    canary_weight = Column(Float, nullable=True, default=0.0)  # 灰度权重 0.0~1.0
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_prompt_versions_agent_name", "agent_name"),
    )


# ─────────────────────── 22. schema_versions ───────────────────────

class SchemaVersion(Base):
    __tablename__ = "schema_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(64), nullable=False)
    version = Column(String(16), nullable=False)
    json_schema = Column(Text, nullable=False)  # JSON Schema 内容
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_schema_versions_agent_name", "agent_name"),
    )


# ─────────────────────── 23. eval_datasets ───────────────────────

class EvalDataset(Base):
    __tablename__ = "eval_datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    test_cases_json = Column(Text, nullable=False)  # JSON 数组
    created_at = Column(DateTime, default=datetime.utcnow)


# ─────────────────────── 24. eval_runs ───────────────────────

class EvalRun(Base):
    __tablename__ = "eval_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("eval_datasets.id"), nullable=False)
    model_name = Column(String(64), nullable=False)
    prompt_version = Column(String(16), nullable=True)
    schema_version = Column(String(16), nullable=True)
    status = Column(String(32), nullable=False, default="RUNNING")
    adoption_rate = Column(Float, nullable=True)
    rejection_rate = Column(Float, nullable=True)
    evidence_coverage_rate = Column(Float, nullable=True)
    schema_pass_rate = Column(Float, nullable=True)
    hallucination_rate = Column(Float, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)


# ─────────────────────── 25. eval_results ───────────────────────

class EvalResult(Base):
    __tablename__ = "eval_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    eval_run_id = Column(Integer, ForeignKey("eval_runs.id"), nullable=False)
    test_case_index = Column(Integer, nullable=False)
    input_json = Column(Text, nullable=True)
    expected_output_json = Column(Text, nullable=True)
    actual_output_json = Column(Text, nullable=True)
    adopted = Column(Integer, nullable=True)  # 0/1
    has_hallucination = Column(Integer, nullable=True)  # 0/1
    schema_valid = Column(Integer, nullable=True)  # 0/1
    evidence_covered = Column(Integer, nullable=True)  # 0/1
    created_at = Column(DateTime, default=datetime.utcnow)