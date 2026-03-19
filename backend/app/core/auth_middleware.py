"""
认证与权限中间件

在请求级别校验角色权限。
当前阶段使用简化实现（Header 传入角色），后续可升级为 JWT。
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.rbac import has_permission, Permission, Role


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
}


class AuthMiddleware(BaseHTTPMiddleware):
    """
    认证与权限中间件。

    从请求 Header 中获取角色信息：
    - X-User-Role: 用户角色（如 risk_ops, finance_ops, admin 等）
    - X-User-Id: 用户 ID

    如果未提供角色，默认作为 admin 处理（开发阶段）。
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # 公开路径跳过认证
        if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        # 获取角色信息
        role = request.headers.get("X-User-Role", "admin")  # 开发阶段默认 admin
        user_id = request.headers.get("X-User-Id", "anonymous")

        # 验证角色有效性
        try:
            Role(role)
        except ValueError:
            return JSONResponse(
                status_code=401,
                content={"detail": f"无效的角色: {role}"},
            )

        # 将用户信息存入 request.state
        request.state.user_role = role
        request.state.user_id = user_id

        # 权限检查（匹配最接近的路径模式）
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
