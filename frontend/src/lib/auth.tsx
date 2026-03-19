"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

// ── 类型定义 ──

export interface AuthUser {
  id: number;
  username: string;
  display_name: string;
  role: string;
  is_active: boolean;
  is_superadmin: boolean;
  last_login_at: string | null;
}

interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  setup: (username: string, displayName: string, password: string) => Promise<void>;
  refreshUser: () => Promise<void>;
}

// ── Token 存储 ──

function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("refresh_token");
}

function setTokens(accessToken: string, refreshToken?: string | null) {
  localStorage.setItem("access_token", accessToken);
  if (refreshToken) {
    localStorage.setItem("refresh_token", refreshToken);
  }
}

function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

// ── 刷新 Token ──

let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;

export async function tryRefreshToken(): Promise<string | null> {
  if (isRefreshing && refreshPromise) return refreshPromise;

  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  isRefreshing = true;
  refreshPromise = (async () => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) return null;
      const data = await res.json();
      setTokens(data.access_token);
      return data.access_token as string;
    } catch {
      return null;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

// ── Context ──

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      let res = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      // Token 过期，尝试刷新
      if (res.status === 401) {
        const newToken = await tryRefreshToken();
        if (newToken) {
          res = await fetch(`${API_BASE}/api/auth/me`, {
            headers: { Authorization: `Bearer ${newToken}` },
          });
        }
      }

      if (res.ok) {
        const data = await res.json();
        setUser(data);
      } else {
        clearTokens();
        setUser(null);
      }
    } catch {
      clearTokens();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const login = async (username: string, password: string) => {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "登录失败");
    }

    const data = await res.json();
    setTokens(data.access_token, data.refresh_token);
    setUser(data.user);
  };

  const setup = async (username: string, displayName: string, password: string) => {
    const res = await fetch(`${API_BASE}/api/auth/setup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, display_name: displayName, password }),
    });

    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "初始化失败");
    }

    const data = await res.json();
    setTokens(data.access_token, data.refresh_token);
    setUser(data.user);
  };

  const logout = () => {
    clearTokens();
    setUser(null);
  };

  const refreshUser = async () => {
    await fetchUser();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        setup,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

export { getAccessToken, clearTokens };
