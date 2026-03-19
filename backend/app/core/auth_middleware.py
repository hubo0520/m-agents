"""
认证与权限中间件

支持 JWT Token 认证（主要方式）和 Header 传入角色（仅 DEBUG 模式）。
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.rbac import has_permission, Permission, Role
from app.core.security import decode_token


# API 路径 → 所需权限的映射
PATH_PERMISSIONS = {
    # 案件
    ("GET", "/api/risk-cases"): Permission.VIEW_CASES,
    ("POST", "/api/risk-cases/{id}/analyze"): Permission.TRIGGER_ANALYSIS,
    ("POST", "/api/cases/{id}/reopen"): Permission.REOPEN_CASE,

    # 审批
    ("GET", "/api/approvals"): Permission.VIEW_APPROVALS,
    ("POST", "/api/approvals/{id}/approve"): Permission.VIEW_APPROVALS,
    ("POST", "/api/approvals/{id}/reject"): Permission.VIEW_APPROVALS,

    # 工作流
    ("GET", "/api/workflows"): Permission.VIEW_WORKFLOWS,
    ("POST", "/api/workflows/{id}/retry"): Permission.RETRY_WORKFLOW,
    ("POST", "/api/workflows/{id}/resume"): Permission.RESUME_WORKFLOW,

    # 配置
    ("POST", "/api/prompt-versions"): Permission.MANAGE_PROMPTS,
    ("POST", "/api/schema-versions"): Permission.MANAGE_SCHEMAS,
    ("POST", "/api/model-policies"): Permission.MANAGE_MODELS,

    # 评测
    ("GET", "/api/evals"): Permission.VIEW_EVALS,
    ("POST", "/api/evals/datasets"): Permission.CREATE_EVALS,
    ("POST", "/api/evals/runs"): Permission.CREATE_EVALS,
}

# 不需要认证的路径
PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/auth/setup",
    "/api/auth/check-init",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """
    认证与权限中间件。

    认证优先级：
    1. Authorization: Bearer <JWT Token>（生产方式）
    2. X-User-Role Header（仅 DEBUG_AUTH=True 时生效）
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # 公开路径跳过认证
        if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        # ── 方式 1: JWT Token 认证 ──
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = decode_token(token)
            if not payload:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Token 无效或已过期"},
                )
            if payload.get("type") != "access":
                return JSONResponse(
                    status_code=401,
                    content={"detail": "请使用 Access Token"},
                )

            # 注入用户信息
            request.state.user_id = payload.get("sub")
            request.state.user_name = payload.get("username")
            request.state.user_role = payload.get("role", "risk_ops")

        # ── 方式 2: Header 调试模式（仅 DEBUG） ──
        elif settings.DEBUG_AUTH:
            role = request.headers.get("X-User-Role", "admin")
            user_id = request.headers.get("X-User-Id", "anonymous")
            try:
                Role(role)
            except ValueError:
                return JSONResponse(
                    status_code=401,
                    content={"detail": f"无效的角色: {role}"},
                )
            request.state.user_role = role
            request.state.user_id = user_id
            request.state.user_name = user_id

        # ── 无认证信息 ──
        else:
            return JSONResponse(
                status_code=401,
                content={"detail": "未提供认证信息"},
            )

        # 权限检查
        role = request.state.user_role
        required_perm = _find_required_permission(method, path)
        if required_perm and not has_permission(role, required_perm):
            return JSONResponse(
                status_code=403,
                content={"detail": f"角色 {role} 无权限: {required_perm.value}"},
            )

        return await call_next(request)


def _find_required_permission(method: str, path: str):
    """查找路径对应的所需权限"""
    # 精确匹配
    for (m, p), perm in PATH_PERMISSIONS.items():
        if m == method:
            # 简化匹配：将路径模式中的 {id} 替换
            pattern_parts = p.split("/")
            path_parts = path.split("/")
            if len(pattern_parts) == len(path_parts):
                match = True
                for pp, actual in zip(pattern_parts, path_parts):
                    if pp.startswith("{") and pp.endswith("}"):
                        continue
                    if pp != actual:
                        match = False
                        break
                if match:
                    return perm
    return None  # 未匹配的路径不做权限限制
