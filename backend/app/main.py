"""商家经营保障 Agent V3 — FastAPI 入口"""
import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api import risk_cases, dashboard, tasks
# V3: 新增 API 模块
from app.api import workflows, approvals, configs, evals
# V3: 认证与用户管理
from app.api import auth as auth_api, users as users_api

# ── 配置 Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
# 降低第三方库噪音
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

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

# V3: RBAC 认证中间件（开发阶段默认 admin，可通过 Header 切换角色）
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


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "3.0.0"}

# 启动时输出 LLM 配置状态
logger.info("🚀 应用启动 | USE_LLM=%s | OPENAI_BASE_URL=%s | MODEL=%s",
            settings.USE_LLM, settings.OPENAI_BASE_URL, settings.OPENAI_MODEL)