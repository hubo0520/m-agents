"""
用户管理 API：用户列表、启用/禁用、修改角色、重置密码、删除用户
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.core.security import hash_password
from app.core.rbac import Role
from app.models.models import User
from app.schemas.auth_schemas import (
    UserResponse, UpdateUserStatusRequest, UpdateUserRoleRequest,
    ResetPasswordRequest, MessageResponse,
)

router = APIRouter(prefix="/api/users", tags=["用户管理"])


def _require_admin(request: Request):
    """检查当前用户是否是管理员"""
    current_role = getattr(request.state, "user_role", None)
    if current_role != Role.ADMIN.value:
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")


def _get_user_or_404(user_id: int, db: Session) -> User:
    """获取用户或返回 404"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


# ─────── 用户列表 ───────

@router.get("", response_model=List[UserResponse])
def list_users(request: Request, db: Session = Depends(get_db)):
    """获取所有用户列表（仅管理员）"""
    _require_admin(request)
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [UserResponse.model_validate(u) for u in users]


# ─────── 启用/禁用用户 ───────

@router.put("/{user_id}/status", response_model=UserResponse)
def update_user_status(
    user_id: int, req: UpdateUserStatusRequest,
    request: Request, db: Session = Depends(get_db),
):
    """启用/禁用用户（仅管理员）"""
    _require_admin(request)
    user = _get_user_or_404(user_id, db)

    current_user_id = getattr(request.state, "user_id", None)

    # 不能禁用自己
    if str(user.id) == str(current_user_id) and not req.is_active:
        raise HTTPException(status_code=400, detail="不能禁用自己的账号")

    # 不能禁用超级管理员
    if user.is_superadmin and not req.is_active:
        raise HTTPException(status_code=403, detail="不能禁用超级管理员")

    user.is_active = req.is_active
    db.commit()
    db.refresh(user)

    action = "启用" if req.is_active else "禁用"
    logger.info("管理员%s用户: %s", action, user.username)
    return UserResponse.model_validate(user)


# ─────── 修改用户角色 ───────

@router.put("/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int, req: UpdateUserRoleRequest,
    request: Request, db: Session = Depends(get_db),
):
    """修改用户角色（仅管理员）"""
    _require_admin(request)
    user = _get_user_or_404(user_id, db)

    # 不能修改超级管理员角色
    if user.is_superadmin:
        raise HTTPException(status_code=403, detail="不能修改超级管理员的角色")

    # 验证角色有效性
    try:
        Role(req.role)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"无效的角色: {req.role}")

    old_role = user.role
    user.role = req.role
    db.commit()
    db.refresh(user)

    logger.info("管理员修改用户角色: %s (%s → %s)", user.username, old_role, req.role)
    return UserResponse.model_validate(user)


# ─────── 重置用户密码 ───────

@router.post("/{user_id}/reset-password", response_model=MessageResponse)
def reset_password(
    user_id: int, req: ResetPasswordRequest,
    request: Request, db: Session = Depends(get_db),
):
    """管理员重置用户密码"""
    _require_admin(request)
    user = _get_user_or_404(user_id, db)

    # 重置超级管理员密码需要自己也是超级管理员
    if user.is_superadmin:
        current_user_id = getattr(request.state, "user_id", None)
        current_user = db.query(User).filter(User.id == int(current_user_id)).first()
        if not current_user or not current_user.is_superadmin:
            raise HTTPException(status_code=403, detail="只有超级管理员可以重置超级管理员的密码")

    user.password_hash = hash_password(req.new_password)
    db.commit()

    logger.info("管理员重置用户密码: %s", user.username)
    return MessageResponse(message="密码重置成功")


# ─────── 删除用户 ───────

@router.delete("/{user_id}", response_model=MessageResponse)
def delete_user(
    user_id: int,
    request: Request, db: Session = Depends(get_db),
):
    """删除用户（仅管理员）"""
    _require_admin(request)
    user = _get_user_or_404(user_id, db)

    current_user_id = getattr(request.state, "user_id", None)

    # 不能删除自己
    if str(user.id) == str(current_user_id):
        raise HTTPException(status_code=400, detail="不能删除自己的账号")

    # 不能删除超级管理员
    if user.is_superadmin:
        raise HTTPException(status_code=403, detail="不能删除超级管理员")

    username = user.username
    db.delete(user)
    db.commit()

    logger.info("管理员删除用户: %s", username)
    return MessageResponse(message="用户已删除")
