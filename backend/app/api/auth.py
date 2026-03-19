"""
认证 API：系统初始化、注册、登录、Token 刷新、修改密码、获取用户信息
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.core.rbac import Role
from app.models.models import User
from app.schemas.auth_schemas import (
    SetupRequest, RegisterRequest, LoginRequest, RefreshRequest,
    ChangePasswordRequest, TokenResponse, UserResponse, MessageResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["认证"])


def _user_to_response(user: User) -> UserResponse:
    """将 User ORM 对象转为响应模型"""
    return UserResponse.model_validate(user)


def _create_tokens(user: User) -> TokenResponse:
    """为用户创建 Access + Refresh Token 并返回"""
    payload = {"sub": str(user.id), "username": user.username, "role": user.role}
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_user_to_response(user),
    )


# ─────── 系统初始化 ───────

@router.post("/setup", response_model=TokenResponse, status_code=201)
def setup(req: SetupRequest, db: Session = Depends(get_db)):
    """
    系统初始化：创建首个超级管理员。
    仅当系统中没有任何用户时可调用。
    """
    if db.query(User).count() > 0:
        raise HTTPException(status_code=403, detail="系统已初始化")

    user = User(
        username=req.username,
        display_name=req.display_name,
        password_hash=hash_password(req.password),
        role=Role.ADMIN.value,
        is_active=True,
        is_superadmin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("系统初始化完成，首个超级管理员: %s", user.username)
    return _create_tokens(user)


# ─────── 管理员注册用户 ───────

@router.post("/register", response_model=UserResponse, status_code=201)
def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """管理员创建新用户"""
    # 权限检查
    current_role = getattr(request.state, "user_role", None)
    if current_role != Role.ADMIN.value:
        raise HTTPException(status_code=403, detail="仅管理员可注册新用户")

    # 验证角色有效性
    try:
        Role(req.role)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"无效的角色: {req.role}")

    # 用户名唯一性检查
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=409, detail="用户名已存在")

    user = User(
        username=req.username,
        display_name=req.display_name,
        password_hash=hash_password(req.password),
        role=req.role,
        is_active=True,
        is_superadmin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("管理员创建新用户: %s (角色: %s)", user.username, user.role)
    return _user_to_response(user)


# ─────── 登录 ───────

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """用户登录，返回 JWT Token"""
    user = db.query(User).filter(User.username == req.username).first()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用，请联系管理员")

    # 更新最后登录时间
    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    logger.info("用户登录: %s", user.username)
    return _create_tokens(user)


# ─────── Token 刷新 ───────

@router.post("/refresh", response_model=TokenResponse)
def refresh(req: RefreshRequest, db: Session = Depends(get_db)):
    """使用 Refresh Token 获取新的 Access Token"""
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh Token 无效或已过期")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    # 只返回新 Access Token，不轮换 Refresh Token
    new_payload = {"sub": str(user.id), "username": user.username, "role": user.role}
    access_token = create_access_token(new_payload)
    return TokenResponse(
        access_token=access_token,
        refresh_token=None,
        user=_user_to_response(user),
    )


# ─────── 修改密码 ───────

@router.post("/change-password", response_model=MessageResponse)
def change_password(req: ChangePasswordRequest, request: Request, db: Session = Depends(get_db)):
    """已登录用户修改自己的密码"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未认证")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")

    user.password_hash = hash_password(req.new_password)
    db.commit()

    logger.info("用户修改密码: %s", user.username)
    return MessageResponse(message="密码修改成功")


# ─────── 获取当前用户信息 ───────

@router.get("/me", response_model=UserResponse)
def get_me(request: Request, db: Session = Depends(get_db)):
    """获取当前登录用户信息"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未认证")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return _user_to_response(user)


# ─────── 检查系统是否已初始化 ───────

@router.get("/check-init")
def check_init(db: Session = Depends(get_db)):
    """检查系统是否已初始化（是否存在用户）"""
    has_users = db.query(User).count() > 0
    return {"initialized": has_users}
