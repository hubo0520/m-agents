"""
通知管理 API

提供通知列表、未读数量、标记已读等接口。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.notification import NotificationService
from app.schemas.notification_schemas import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
)

router = APIRouter(prefix="/api", tags=["通知管理"])


def _get_user_id(request: Request) -> str:
    """从请求中获取当前用户 ID"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未认证")
    return str(user_id)


# ───────────────── GET /api/notifications ─────────────────

@router.get("/notifications", response_model=NotificationListResponse)
def get_notifications(
    request: Request,
    is_read: bool = Query(None, description="按已读状态过滤"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取当前用户的通知列表"""
    user_id = _get_user_id(request)
    items, total = NotificationService.get_list(db, user_id, is_read, page, page_size)
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        page=page,
        page_size=page_size,
    )


# ───────────────── GET /api/notifications/unread-count ─────

@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    request: Request,
    db: Session = Depends(get_db),
):
    """获取当前用户的未读通知数量"""
    user_id = _get_user_id(request)
    count = NotificationService.get_unread_count(db, user_id)
    return UnreadCountResponse(unread_count=count)


# ───────────────── PUT /api/notifications/{id}/read ────────

@router.put("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """标记单条通知已读"""
    user_id = _get_user_id(request)
    success = NotificationService.mark_read(db, notification_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="通知不存在")
    db.commit()
    return {"status": "ok"}


# ───────────────── PUT /api/notifications/read-all ─────────

@router.put("/notifications/read-all")
def mark_all_read(
    request: Request,
    db: Session = Depends(get_db),
):
    """全部标记已读"""
    user_id = _get_user_id(request)
    count = NotificationService.mark_all_read(db, user_id)
    db.commit()
    return {"status": "ok", "updated_count": count}
