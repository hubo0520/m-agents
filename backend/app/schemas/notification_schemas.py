"""
通知 Pydantic Schema 定义
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    """单条通知响应"""
    id: int
    user_id: str
    title: str
    content: Optional[str] = None
    type: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """通知列表响应"""
    items: List[NotificationResponse]
    total: int
    page: int
    page_size: int


class UnreadCountResponse(BaseModel):
    """未读通知数量响应"""
    unread_count: int
