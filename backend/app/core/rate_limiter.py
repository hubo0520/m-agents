"""
API 限流模块 — 滑动窗口计数器 + FastAPI 中间件 + 分析任务防重复

提供三个核心组件：
1. SlidingWindowRateLimiter: 基于内存的滑动窗口限流器
2. RateLimitMiddleware: FastAPI 中间件，双维度（用户 ID + IP）限流
3. AnalysisLock: 分析任务防重复锁
"""
import time
import threading
from collections import defaultdict
from typing import Optional, Tuple

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings


# ═══════════════════════════════════════════════════════════════
# 滑动窗口限流器
# ═══════════════════════════════════════════════════════════════

class SlidingWindowRateLimiter:
    """
    基于内存的滑动窗口计数器限流器。

    每个 key（用户 ID 或 IP）维护一个时间戳列表，
    仅保留窗口内的请求记录，超出窗口的自动清理。
    """

    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> Tuple[bool, int, float]:
        """
        检查请求是否允许通过。

        Args:
            key: 限流维度标识（用户 ID 或 IP 地址）

        Returns:
            (allowed, remaining, retry_after)
            - allowed: 是否允许
            - remaining: 剩余可用次数
            - retry_after: 如果被限流，建议等待秒数
        """
        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            # 清理窗口外的旧记录
            timestamps = self._requests[key]
            self._requests[key] = [t for t in timestamps if t > window_start]
            timestamps = self._requests[key]

            current_count = len(timestamps)

            if current_count >= self.max_requests:
                # 计算最早请求过期的时间
                retry_after = round(timestamps[0] - window_start, 1)
                if retry_after <= 0:
                    retry_after = 1.0
                return False, 0, retry_after

            # 允许通过，记录时间戳
            timestamps.append(now)
            remaining = self.max_requests - len(timestamps)
            return True, remaining, 0.0

    def get_count(self, key: str) -> int:
        """获取当前窗口内的请求数"""
        now = time.time()
        window_start = now - self.window_seconds
        with self._lock:
            timestamps = self._requests.get(key, [])
            return len([t for t in timestamps if t > window_start])


# ═══════════════════════════════════════════════════════════════
# 预构建的限流器实例
# ═══════════════════════════════════════════════════════════════

# 普通 API 限流器
_default_limiter = SlidingWindowRateLimiter(
    max_requests=settings.RATE_LIMIT_DEFAULT, window_seconds=60
)

# 分析类 API 限流器（更严格）
_analysis_limiter = SlidingWindowRateLimiter(
    max_requests=settings.RATE_LIMIT_ANALYSIS, window_seconds=60
)

# 认证类 API 限流器（按 IP）
_auth_limiter = SlidingWindowRateLimiter(
    max_requests=settings.RATE_LIMIT_AUTH, window_seconds=60
)

# 豁免限流的路径
EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

# 分析类 API 路径（仅用于文档说明，实际匹配逻辑在 _is_analysis_path 函数中）
ANALYSIS_PATHS = {"/api/workflows/start", "/api/cases/{id}/reopen"}

# 认证类 API 路径前缀
AUTH_PATHS = {"/api/auth/login", "/api/auth/refresh", "/api/auth/setup", "/api/auth/check-init"}


def _is_analysis_path(path: str) -> bool:
    """判断是否为分析类 API"""
    if path == "/api/workflows/start":
        return True
    # /api/cases/{id}/reopen 也算分析类
    if path.startswith("/api/cases/") and path.endswith("/reopen"):
        return True
    return False


def _is_auth_path(path: str) -> bool:
    """判断是否为认证类 API"""
    return path in AUTH_PATHS


# ═══════════════════════════════════════════════════════════════
# FastAPI 限流中间件
# ═══════════════════════════════════════════════════════════════

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    API 请求限流中间件。

    限流策略：
    - 已认证用户：按 user_id 限流
    - 未认证请求：按 IP 限流
    - 分析 API：使用更严格的限流窗口
    - /health 等端点豁免限流
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        start_time = time.time()

        # 豁免路径
        if path in EXEMPT_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        # 确定限流 key 和限流器
        user_id = getattr(request.state, "user_id", None) if hasattr(request, "state") else None
        client_ip = request.client.host if request.client else "unknown"

        if _is_auth_path(path):
            # 认证类 API：按 IP 限流
            limiter = _auth_limiter
            rate_key = f"ip:{client_ip}"
        elif _is_analysis_path(path):
            # 分析类 API：按用户限流（更严格）
            limiter = _analysis_limiter
            rate_key = f"user:{user_id}" if user_id else f"ip:{client_ip}"
        else:
            # 普通 API：按用户限流
            limiter = _default_limiter
            rate_key = f"user:{user_id}" if user_id else f"ip:{client_ip}"

        allowed, remaining, retry_after = limiter.is_allowed(rate_key)

        if not allowed:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                "⚠️ 限流触发 | key={} | path={} | count={}/{} | elapsed_ms={}",
                rate_key, path, limiter.get_count(rate_key),
                limiter.max_requests, elapsed_ms,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "detail": "请求过于频繁，请稍后再试",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(int(retry_after))},
            )

        # 允许通过，执行下游
        response = await call_next(request)

        # 添加剩余次数响应头
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response


# ═══════════════════════════════════════════════════════════════
# 分析任务防重复锁
# ═══════════════════════════════════════════════════════════════

class AnalysisLock:
    """
    基于内存 Set 跟踪正在分析的案件 ID，
    防止同一案件在上一次分析未完成时被重复触发。
    """

    def __init__(self):
        self._active_cases: set[int] = set()
        self._lock = threading.Lock()

    def acquire(self, case_id: int) -> bool:
        """尝试获取锁。成功返回 True，案件已在分析中返回 False。"""
        with self._lock:
            if case_id in self._active_cases:
                return False
            self._active_cases.add(case_id)
            return True

    def release(self, case_id: int) -> None:
        """释放锁"""
        with self._lock:
            self._active_cases.discard(case_id)

    def is_locked(self, case_id: int) -> bool:
        """检查案件是否正在分析"""
        with self._lock:
            return case_id in self._active_cases


# 全局实例
analysis_lock = AnalysisLock()
