"""Pydantic 请求/响应 Schema"""
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime


# ───────── 响应 Schema ─────────

class MerchantInfo(BaseModel):
    id: int
    name: str
    industry: str
    settlement_cycle_days: int
    store_level: str

    class Config:
        from_attributes = True


class RiskCaseListItem(BaseModel):
    id: int
    merchant_id: int
    merchant_name: str
    industry: str
    risk_score: Optional[float] = None
    risk_level: str
    status: str
    return_rate_7d: Optional[float] = None
    baseline_return_rate: Optional[float] = None
    return_amplification: Optional[float] = None
    predicted_gap: Optional[float] = None
    recommendation_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int


class EvidenceItemResponse(BaseModel):
    id: int
    evidence_type: str
    source_table: Optional[str] = None
    source_id: Optional[int] = None
    summary: Optional[str] = None
    importance_score: Optional[float] = None

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    actor: Optional[str] = None
    action: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    merchant_count: int
    new_high_risk_count: int
    total_predicted_gap: float
    avg_settlement_delay: float


class TrendDataPoint(BaseModel):
    date: str
    order_amount: float
    return_rate: float
    refund_amount: float
    settlement_amount: float


class CaseDetailResponse(BaseModel):
    id: int
    merchant: MerchantInfo
    risk_score: Optional[float] = None
    risk_level: str
    status: str
    trigger_json: Optional[Any] = None
    agent_output: Optional[Any] = None
    metrics: Optional[dict] = None
    trend_data: Optional[List[TrendDataPoint]] = None
    forecast: Optional[dict] = None
    evidence: List[EvidenceItemResponse] = []
    recommendations: List[Any] = []
    reviews: List[Any] = []
    audit_logs: List[AuditLogResponse] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ───────── 请求 Schema ─────────

class ReviewRequest(BaseModel):
    decision: str  # approve / approve_with_changes / reject
    comment: str = ""
    final_actions: Optional[List[Any]] = None
    reviewer_id: str = "operator"


# ───────── V2: 任务相关 Schema ─────────

class FinancingApplicationCreate(BaseModel):
    merchant_id: int
    amount_requested: float
    reason: str = "cash flow gap"


class FinancingApplicationResponse(BaseModel):
    id: int
    merchant_id: int
    case_id: int
    recommendation_id: Optional[int] = None
    amount_requested: float
    loan_purpose: Optional[str] = None
    repayment_plan: Optional[Any] = None
    merchant_info_snapshot: Optional[Any] = None
    historical_settlement: Optional[Any] = None
    approval_status: str
    reviewer_comment: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ClaimCreate(BaseModel):
    merchant_id: int
    claim_amount: float
    claim_reason: str = "product defect"


class ClaimResponse(BaseModel):
    id: int
    merchant_id: int
    case_id: int
    recommendation_id: Optional[int] = None
    policy_id: Optional[int] = None
    claim_amount: float
    claim_reason: Optional[str] = None
    evidence_snapshot: Optional[Any] = None
    return_details: Optional[Any] = None
    claim_status: str
    reviewer_comment: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ManualReviewCreate(BaseModel):
    merchant_id: int
    task_type: str = "return_fraud"
    evidence_ids: Optional[List[int]] = None


class ManualReviewResponse(BaseModel):
    id: int
    merchant_id: int
    case_id: int
    recommendation_id: Optional[int] = None
    task_type: str
    review_reason: Optional[str] = None
    evidence_ids: Optional[Any] = None
    assigned_to: Optional[str] = None
    status: str
    review_result: Optional[str] = None
    reviewer_comment: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None


class UnifiedTaskListItem(BaseModel):
    task_id: int
    task_type: str  # financing / claim / manual_review
    merchant_id: int
    merchant_name: str
    case_id: int
    status: str
    amount: Optional[float] = None
    assigned_to: Optional[str] = None
    created_at: Optional[str] = None


class TaskStatusUpdate(BaseModel):
    new_status: str
    comment: str = ""
    reviewer_id: str = "operator"
