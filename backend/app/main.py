"""商家经营保障 Agent V3 — FastAPI 入口"""
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging_config import setup_logging
from app.api import risk_cases, dashboard, tasks
# V3: 新增 API 模块
from app.api import workflows, approvals, configs, evals
# V4: 对话式分析 & 可观测
from app.api import conversations as conversations_api
from app.api import observability as observability_api
# V3: 认证与用户管理
from app.api import auth as auth_api, users as users_api

# 初始化日志配置
setup_logging()

# 启动时创建所有表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="商家经营保障 Agent V3",
    description="面向内部运营人员的多 Agent 风控执行系统",
    version="3.0.0",
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 限流中间件（需在 Auth 之后执行，所以先 add —— Starlette 栈式：后 add 先执行）
from app.core.rate_limiter import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)

# V3: RBAC 认证中间件（后 add → 先执行，确保 user_id 已注入 request.state）
from app.core.auth_middleware import AuthMiddleware
app.add_middleware(AuthMiddleware)

# 注册路由 — V1/V2
app.include_router(risk_cases.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")

# 注册路由 — V3
app.include_router(workflows.router)
app.include_router(approvals.router)
app.include_router(configs.router)
app.include_router(evals.router)

# 注册路由 — 认证与用户管理
app.include_router(auth_api.router)
app.include_router(users_api.router)

# 注册路由 — V4 对话式分析
app.include_router(conversations_api.router)
app.include_router(observability_api.router)

# 注册路由 — V5 通知系统
from app.api import notifications as notifications_api
app.include_router(notifications_api.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "3.0.0"}

# 导入异常处理相关模块
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException
from app.core.error_codes import INTERNAL_SERVER_ERROR, VALIDATION_ERROR


# 全局异常处理器
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """处理自定义应用异常"""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误"""
    return JSONResponse(
        status_code=422,
        content={
            "error": VALIDATION_ERROR,
            "detail": "请求数据验证失败",
            "status_code": 422,
            "errors": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常兜底处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": INTERNAL_SERVER_ERROR,
            "detail": "服务器内部错误",
            "status_code": 500
        }
    )


# 启动时输出 LLM 配置状态
logger.info("🚀 应用启动 | USE_LLM={} | OPENAI_BASE_URL={} | MODEL={}",
            settings.USE_LLM, settings.OPENAI_BASE_URL, settings.OPENAI_MODEL)

# 启动时输出 RAG / 向量存储状态
try:
    from app.core.vector_store import is_vector_store_available, _chromadb_available, _chromadb_init_error
    if _chromadb_available:
        vs_ok = is_vector_store_available()
        logger.info("🔍 RAG 状态 | chromadb_module=✅ | vector_store_ready={} | EMBEDDING_MODEL={}",
                     vs_ok, settings.EMBEDDING_MODEL)
    else:
        logger.warning("🔍 RAG 状态 | chromadb_module=❌ 不可用 | 原因={} | 对话将降级为 agent_output_json 模式",
                        _chromadb_init_error or "未知")
except Exception as e:
    logger.warning("🔍 RAG 状态检测失败: {}", e)