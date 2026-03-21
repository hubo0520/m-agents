"""认证与用户管理相关的 Pydantic 模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── 请求模型 ──

class SetupRequest(BaseModel):
    """系统初始化请求"""
    username: str = Field(..., min_length=2, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=6, max_length=128)


class RegisterRequest(BaseModel):
    """管理员注册新用户请求"""
    username: str = Field(..., min_length=2, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(..., description="角色：admin / risk_ops / finance_ops / claim_ops / compliance")


class PublicRegisterRequest(BaseModel):
    """公开注册请求（无需管理员权限）"""
    username: str = Field(..., min_length=2, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class RefreshRequest(BaseModel):
    """Token 刷新请求"""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=128)


class ResetPasswordRequest(BaseModel):
    """管理员重置用户密码请求"""
    new_password: str = Field(..., min_length=6, max_length=128)


class UpdateUserStatusRequest(BaseModel):
    """启用/禁用用户请求"""
    is_active: bool


class UpdateUserRoleRequest(BaseModel):
    """修改用户角色请求"""
    role: str = Field(..., description="新角色")


# ── 响应模型 ──

class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    display_name: str
    role: str
    is_active: bool
    is_superadmin: bool
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """登录/刷新返回的 Token 响应"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional[UserResponse] = None


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
