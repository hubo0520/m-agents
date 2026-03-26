/**
 * 统一 API 客户端：自动携带 Token、处理 401 自动刷新 + 429 限流友好处理
 */

import { getAccessToken, clearTokens, tryRefreshToken } from "./auth";
import { toast } from "sonner";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

// ═══════════════════════════════════════════════════════════════
// 限流状态管理 — 通过自定义事件通知全局 Banner
// ═══════════════════════════════════════════════════════════════

/** 派发限流事件，通知全局 RateLimitBanner 组件 */
function emitRateLimitEvent(retryAfter: number) {
  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new CustomEvent("rate-limit-triggered", { detail: { retryAfter } })
    );
  }
}

/**
 * 带认证的 API 请求工具函数
 * - 自动携带 Authorization Header
 * - 遇到 401 自动尝试刷新 Token
 * - 遇到 429 展示去重 toast + GET 请求自动重试一次
 * - 刷新失败跳转登录页
 */
export async function authFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAccessToken();
  const method = (options?.method || "GET").toUpperCase();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string> || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  // Token 过期，尝试刷新
  if (res.status === 401 && token) {
    const newToken = await tryRefreshToken();
    if (newToken) {
      headers["Authorization"] = `Bearer ${newToken}`;
      res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
      });
    } else {
      // 刷新也失败，清除 Token 并跳转登录
      clearTokens();
      toast.error("登录已过期，请重新登录");
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new Error("认证已过期，请重新登录");
    }
  }

  // ── 429 限流处理：去重 toast + GET 自动重试 ──
  if (res.status === 429) {
    const detail = await res.text();
    let retryAfter = 0;
    try {
      const parsed = JSON.parse(detail);
      retryAfter = Math.ceil(parsed.retry_after || 0);
    } catch {
      retryAfter = parseInt(res.headers.get("Retry-After") || "0", 10);
    }

    // 去重 toast：使用固定 id，多个并发 429 只展示一次
    const waitMsg = retryAfter > 0 ? `，请 ${retryAfter} 秒后再试` : "，请稍后再试";
    toast.warning(`请求过于频繁${waitMsg}`, {
      id: "rate-limit",
      duration: Math.max(retryAfter * 1000, 5000),
    });

    // 派发限流事件，通知全局 Banner
    emitRateLimitEvent(retryAfter);

    // 仅对 GET 请求自动重试一次（幂等操作）
    if (method === "GET" && retryAfter > 0) {
      await new Promise((resolve) => setTimeout(resolve, retryAfter * 1000));
      const retryRes = await fetch(`${API_BASE}${path}`, { ...options, headers });
      if (retryRes.ok) {
        return retryRes.json();
      }
      // 重试仍失败，放弃
    }

    throw new Error("请求过于频繁，请稍后再试");
  }

  if (!res.ok) {
    const detail = await res.text();
    // 解析后端标准化错误格式
    let errorMessage = `请求失败 (${res.status})`;
    try {
      const parsed = JSON.parse(detail);
      errorMessage = parsed.detail || parsed.error || errorMessage;
    } catch {
      if (detail) errorMessage = detail;
    }

    // 根据状态码展示不同 Toast
    if (res.status === 401) {
      toast.error("登录已过期，请重新登录");
      clearTokens();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    } else if (res.status === 403) {
      toast.error("没有权限执行此操作");
    } else if (res.status >= 500) {
      toast.error("服务器错误，请稍后重试");
    } else if (res.status >= 400) {
      toast.error(errorMessage);
    }

    throw new Error(errorMessage);
  }

  return res.json();
}

/**
 * GET 请求快捷方法
 */
export function apiGet<T>(path: string): Promise<T> {
  return authFetch<T>(path, { method: "GET" });
}

/**
 * POST 请求快捷方法
 */
export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return authFetch<T>(path, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * PUT 请求快捷方法
 */
export function apiPut<T>(path: string, body?: unknown): Promise<T> {
  return authFetch<T>(path, {
    method: "PUT",
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * DELETE 请求快捷方法
 */
export function apiDelete<T>(path: string): Promise<T> {
  return authFetch<T>(path, { method: "DELETE" });
}
