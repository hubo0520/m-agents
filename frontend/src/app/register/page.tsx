"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, register } = useAuth();

  // 表单状态
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // 已登录 → 跳转首页
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/");
    }
  }, [isLoading, isAuthenticated, router]);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // 客户端验证
    if (password.length < 6) {
      setError("密码至少 6 位");
      return;
    }
    if (password !== confirmPassword) {
      setError("两次密码输入不一致");
      return;
    }

    setSubmitting(true);
    try {
      await register(username, displayName, password);
      router.replace("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "注册失败");
    } finally {
      setSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-white to-blue-50/30 px-4">
      <div className="w-full max-w-[400px]">
        {/* 品牌区 */}
        <div className="text-center mb-8">
          <div className="inline-flex w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 items-center justify-center shadow-lg shadow-blue-500/20 mb-4">
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-slate-800">商家经营保障 Agent</h1>
          <p className="text-sm text-slate-400 mt-1">创建账号，快速体验系统功能</p>
        </div>

        {/* 卡片 */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/60 p-6 sm:p-8">
          <h2 className="text-base font-semibold text-slate-800 mb-6">注册新账号</h2>

          {error && (
            <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-100 text-sm text-red-600">
              {error}
            </div>
          )}

          <form onSubmit={handleRegister} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">用户名</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
                autoComplete="username"
                minLength={2}
                maxLength={64}
                placeholder="2-64 位字符"
                className="w-full px-3 py-2.5 text-base border border-slate-200 rounded-lg bg-slate-50/50 focus:bg-white focus:border-blue-400 focus:ring-2 focus:ring-blue-500/10 outline-none transition-all placeholder:text-slate-300"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">显示名称</label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
                minLength={1}
                maxLength={128}
                placeholder="用于前端展示的名称"
                className="w-full px-3 py-2.5 text-base border border-slate-200 rounded-lg bg-slate-50/50 focus:bg-white focus:border-blue-400 focus:ring-2 focus:ring-blue-500/10 outline-none transition-all placeholder:text-slate-300"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">密码</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
                minLength={6}
                maxLength={128}
                placeholder="至少 6 位字符"
                className="w-full px-3 py-2.5 text-base border border-slate-200 rounded-lg bg-slate-50/50 focus:bg-white focus:border-blue-400 focus:ring-2 focus:ring-blue-500/10 outline-none transition-all placeholder:text-slate-300"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">确认密码</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
                placeholder="请再次输入密码"
                className="w-full px-3 py-2.5 text-base border border-slate-200 rounded-lg bg-slate-50/50 focus:bg-white focus:border-blue-400 focus:ring-2 focus:ring-blue-500/10 outline-none transition-all placeholder:text-slate-300"
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
                  注册中...
                </span>
              ) : (
                "注册并进入系统"
              )}
            </button>
          </form>

          <p className="text-xs text-slate-400 text-center mt-4">
            已有账号？
            <Link href="/login" className="text-blue-500 hover:text-blue-600 ml-1">
              去登录
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
