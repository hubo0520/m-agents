"use client";

import { useState } from "react";
import { authFetch } from "@/lib/api-client";

interface ChangePasswordModalProps {
  onClose: () => void;
}

export function ChangePasswordModal({ onClose }: ChangePasswordModalProps) {
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (newPassword.length < 6) {
      setError("新密码至少 6 位");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("两次输入的新密码不一致");
      return;
    }

    setSubmitting(true);
    try {
      await authFetch("/api/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
      });
      setSuccess(true);
      setTimeout(onClose, 1500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "修改失败";
      // 尝试从 API 错误信息中提取 detail
      if (msg.includes("旧密码错误")) {
        setError("旧密码错误");
      } else {
        setError(msg);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 遮罩 */}
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />

      {/* 弹窗 */}
      <div className="relative bg-white rounded-2xl shadow-xl border border-slate-200/60 w-full max-w-[400px] mx-4 p-6">
        <h2 className="text-base font-semibold text-slate-800 mb-5">修改密码</h2>

        {success ? (
          <div className="text-center py-4">
            <div className="w-10 h-10 mx-auto mb-3 rounded-full bg-green-50 flex items-center justify-center">
              <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
            </div>
            <p className="text-sm text-slate-600">密码修改成功</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="px-3 py-2.5 rounded-lg bg-red-50 border border-red-100 text-sm text-red-600">
                {error}
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">旧密码</label>
              <input
                type="password"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                required
                autoFocus
                className="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-lg bg-slate-50/50 focus:bg-white focus:border-blue-400 focus:ring-2 focus:ring-blue-500/10 outline-none transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">新密码</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                placeholder="至少 6 位字符"
                className="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-lg bg-slate-50/50 focus:bg-white focus:border-blue-400 focus:ring-2 focus:ring-blue-500/10 outline-none transition-all placeholder:text-slate-300"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">确认新密码</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                className="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-lg bg-slate-50/50 focus:bg-white focus:border-blue-400 focus:ring-2 focus:ring-blue-500/10 outline-none transition-all"
              />
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 py-2.5 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
              >
                取消
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="flex-1 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {submitting ? "提交中..." : "确认修改"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
