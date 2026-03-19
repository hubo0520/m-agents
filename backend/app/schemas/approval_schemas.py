"""审批相关 Pydantic Schema"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class ApprovalTaskResponse(BaseModel):
    """审批任务响应"""
    id: int
    workflow_run_id: Optional[int] = None
    case_id: int
    approval_type: str
    assignee_role: Optional[str] = None
    status: str
    payload_json: Optional[str] = None
    reviewer: Optional[str] = None
    reviewed_at: Optional[str] = None
    comment: Optional[str] = None
    final_action_json: Optional[str] = None
    created_at: Optional[str] = None
    due_at: Optional[str] = None

    class Config:
        from_attributes = True


class ApproveRequest(BaseModel):
    """批准请求"""
    reviewer_id: str = Field(default="system", description="审批人 ID")
    comment: str = Field(default="", description="审批意见")


class RejectRequest(BaseModel):
    """驳回请求"""
    reviewer_id: str = Field(default="system", description="审批人 ID")
    comment: str = Field(..., min_length=1, description="驳回理由（必填）")


class ReviseAndApproveRequest(BaseModel):
    """修改后批准请求"""
    reviewer_id: str = Field(default="system", description="审批人 ID")
    comment: str = Field(default="", description="审批意见")
    revised_payload: dict = Field(..., description="修改后的审批内容")


class BatchApproveRequest(BaseModel):
    """批量审批请求"""
    approval_ids: List[int] = Field(..., description="审批任务 ID 列表")
    action: str = Field(..., description="操作类型: approve / reject")
    reviewer_id: str = Field(default="system", description="审批人 ID")
    comment: str = Field(default="", description="审批意见")
