/**
 * 统一 API 客户端：自动携带 Token、处理 401 自动刷新逻辑
 */

import { getAccessToken, clearTokens, tryRefreshToken } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

/**
 * 带认证的 API 请求工具函数
 * - 自动携带 Authorization Header
 * - 遇到 401 自动尝试刷新 Token
 * - 刷新失败跳转登录页
 */
export async function authFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAccessToken();

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
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new Error("认证已过期，请重新登录");
    }
  }

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API error ${res.status}: ${detail}`);
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
