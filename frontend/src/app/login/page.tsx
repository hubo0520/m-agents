"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export default function LoginPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, login, setup } = useAuth();

  // 系统初始化状态
  const [initialized, setInitialized] = useState<boolean | null>(null);
  const [isSetupMode, setIsSetupMode] = useState(false);

  // 表单状态
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // 检查系统是否已初始化
  useEffect(() => {
    fetch(`${API_BASE}/api/auth/check-init`)
      .then((r) => r.json())
      .then((data) => {
        setInitialized(data.initialized);
        if (!data.initialized) setIsSetupMode(true);
      })
      .catch(() => setInitialized(true));
  }, []);

  // 已登录 → 跳转首页
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/");
    }
  }, [isLoading, isAuthenticated, router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(username, password);
      router.replace("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 6) {
      setError("密码至少 6 位");
      return;
    }
    setSubmitting(true);
    try {
      await setup(username, displayName, password);
      router.replace("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "初始化失败");
    } finally {
      setSubmitting(false);
    }
  };

  if (isLoading || initialized === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-white to-blue-50/30">
      <div className="w-full max-w-[400px] mx-4">
        {/* 品牌区 */}
        <div className="text-center mb-8">
          <div className="inline-flex w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 items-center justify-center shadow-lg shadow-blue-500/20 mb-4">
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-slate-800">商家经营保障 Agent</h1>
          <p className="text-sm text-slate-400 mt-1">
            {isSetupMode ? "首次使用，请创建管理员账号" : "登录以继续操作"}
          </p>
        </div>

        {/* 卡片 */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/60 p-8">
          <h2 className="text-base font-semibold text-slate-800 mb-6">
            {isSetupMode ? "系统初始化" : "账号登录"}
          </h2>

          {error && (
            <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-100 text-sm text-red-600">
              {error}
            </div>
          )}

          <form onSubmit={isSetupMode ? handleSetup : handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">用户名</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
                placeholder="请输入用户名"
                className="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-lg bg-slate-50/50 focus:bg-white focus:border-blue-400 focus:ring-2 focus:ring-blue-500/10 outline-none transition-all placeholder:text-slate-300"
              />
            </div>

            {isSetupMode && (
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">显示名称</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  required
                  placeholder="用于前端展示的名称"
                  className="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-lg bg-slate-50/50 focus:bg-white focus:border-blue-400 focus:ring-2 focus:ring-blue-500/10 outline-none transition-all placeholder:text-slate-300"
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">密码</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder={isSetupMode ? "至少 6 位字符" : "请输入密码"}
                className="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-lg bg-slate-50/50 focus:bg-white focus:border-blue-400 focus:ring-2 focus:ring-blue-500/10 outline-none transition-all placeholder:text-slate-300"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-2"
            >
              {submitting ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  {isSetupMode ? "创建中..." : "登录中..."}
                </span>
              ) : (
                isSetupMode ? "创建管理员并进入系统" : "登 录"
              )}
            </button>
          </form>

          {/* 初始化模式下不显示切换按钮 */}
          {initialized && !isSetupMode && (
            <p className="text-xs text-slate-400 text-center mt-4">
              请联系管理员获取账号
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
