"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

interface UserItem {
  id: number;
  username: string;
  display_name: string;
  role: string;
  is_active: boolean;
  is_superadmin: boolean;
  last_login_at: string | null;
  created_at: string | null;
}

const ROLE_LABELS: Record<string, string> = {
  admin: "管理员",
  risk_ops: "风险运营",
  finance_ops: "融资运营",
  claim_ops: "理赔运营",
  compliance: "合规复核",
};

const ROLE_OPTIONS = [
  { value: "admin", label: "管理员" },
  { value: "risk_ops", label: "风险运营" },
  { value: "finance_ops", label: "融资运营" },
  { value: "claim_ops", label: "理赔运营" },
  { value: "compliance", label: "合规复核" },
];

export function UserManagementTab() {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showResetModal, setShowResetModal] = useState<UserItem | null>(null);
  const [showRoleModal, setShowRoleModal] = useState<UserItem | null>(null);
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const fetchUsers = () => {
    setLoading(true);
    apiGet<UserItem[]>("/api/users")
      .then(setUsers)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleToggleStatus = async (user: UserItem) => {
    setActionLoading(user.id);
    try {
      await apiPut(`/api/users/${user.id}/status`, { is_active: !user.is_active });
      fetchUsers();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "操作失败");
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (user: UserItem) => {
    if (!confirm(`确定要删除用户 "${user.display_name}" 吗？此操作不可撤销。`)) return;
    setActionLoading(user.id);
    try {
      await apiDelete(`/api/users/${user.id}`);
      fetchUsers();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "删除失败");
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-800">用户列表</h3>
        <button
          onClick={() => setShowCreateModal(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-xs font-medium hover:bg-blue-700 transition-colors"
        >
          + 新建用户
        </button>
      </div>

      <Card padding="none" className="overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100">
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">用户名</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">显示名称</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">角色</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">状态</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">最后登录</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="px-5 py-8 text-center text-slate-400 text-sm">加载中...</td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-5 py-8 text-center text-slate-400 text-sm">暂无用户</td>
              </tr>
            ) : (
              users.map((u) => (
                <tr key={u.id} className="border-b border-slate-50 table-row-hover">
                  <td className="px-5 py-3.5 font-mono text-xs text-slate-700">
                    {u.username}
                    {u.is_superadmin && (
                      <span className="ml-1.5 text-[10px] text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">超管</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5 font-medium text-slate-800">{u.display_name}</td>
                  <td className="px-5 py-3.5">
                    <Badge variant="muted" size="sm">{ROLE_LABELS[u.role] || u.role}</Badge>
                  </td>
                  <td className="px-5 py-3.5">
                    <Badge variant={u.is_active ? "success" : "danger"} size="sm" dot>
                      {u.is_active ? "启用" : "禁用"}
                    </Badge>
                  </td>
                  <td className="px-5 py-3.5 text-xs text-slate-400">
                    {u.last_login_at ? new Date(u.last_login_at).toLocaleString("zh-CN") : "从未登录"}
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex gap-2">
                      <button
                        onClick={() => setShowRoleModal(u)}
                        disabled={u.is_superadmin || actionLoading === u.id}
                        className="text-xs text-blue-600 hover:text-blue-700 disabled:text-slate-300 disabled:cursor-not-allowed"
                      >
                        改角色
                      </button>
                      <button
                        onClick={() => handleToggleStatus(u)}
                        disabled={u.is_superadmin || actionLoading === u.id}
                        className={`text-xs ${u.is_active ? "text-amber-600 hover:text-amber-700" : "text-green-600 hover:text-green-700"} disabled:text-slate-300 disabled:cursor-not-allowed`}
                      >
                        {u.is_active ? "禁用" : "启用"}
                      </button>
                      <button
                        onClick={() => setShowResetModal(u)}
                        disabled={actionLoading === u.id}
                        className="text-xs text-slate-600 hover:text-slate-700 disabled:text-slate-300"
                      >
                        重置密码
                      </button>
                      <button
                        onClick={() => handleDelete(u)}
                        disabled={u.is_superadmin || actionLoading === u.id}
                        className="text-xs text-red-500 hover:text-red-600 disabled:text-slate-300 disabled:cursor-not-allowed"
                      >
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </Card>

      {/* 新建用户弹窗 */}
      {showCreateModal && (
        <CreateUserModal
          onClose={() => setShowCreateModal(false)}
          onCreated={fetchUsers}
        />
      )}

      {/* 重置密码弹窗 */}
      {showResetModal && (
        <ResetPasswordModal
          user={showResetModal}
          onClose={() => setShowResetModal(null)}
          onReset={fetchUsers}
        />
      )}

      {/* 修改角色弹窗 */}
      {showRoleModal && (
        <ChangeRoleModal
          user={showRoleModal}
          onClose={() => setShowRoleModal(null)}
          onChanged={fetchUsers}
        />
      )}
    </div>
  );
}

// ─────── 新建用户弹窗 ───────

function CreateUserModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("risk_ops");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 6) { setError("密码至少 6 位"); return; }
    setSubmitting(true);
    try {
      await apiPost("/api/auth/register", { username, display_name: displayName, password, role });
      onCreated();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "创建失败");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ModalWrapper onClose={onClose} title="新建用户">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBox message={error} />}
        <FormField label="用户名">
          <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus className="form-input" placeholder="登录用户名" />
        </FormField>
        <FormField label="显示名称">
          <input type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)} required className="form-input" placeholder="前端显示名称" />
        </FormField>
        <FormField label="密码">
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required className="form-input" placeholder="至少 6 位" />
        </FormField>
        <FormField label="角色">
          <select value={role} onChange={(e) => setRole(e.target.value)} className="form-input">
            {ROLE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </FormField>
        <ModalActions onClose={onClose} submitting={submitting} label="创建用户" />
      </form>
    </ModalWrapper>
  );
}

// ─────── 重置密码弹窗 ───────

function ResetPasswordModal({ user, onClose, onReset }: { user: UserItem; onClose: () => void; onReset: () => void }) {
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (newPassword.length < 6) { setError("密码至少 6 位"); return; }
    setSubmitting(true);
    try {
      await apiPost(`/api/users/${user.id}/reset-password`, { new_password: newPassword });
      onReset();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "重置失败");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ModalWrapper onClose={onClose} title={`重置密码 — ${user.display_name}`}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBox message={error} />}
        <FormField label="新密码">
          <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required autoFocus className="form-input" placeholder="至少 6 位" />
        </FormField>
        <ModalActions onClose={onClose} submitting={submitting} label="重置密码" />
      </form>
    </ModalWrapper>
  );
}

// ─────── 修改角色弹窗 ───────

function ChangeRoleModal({ user, onClose, onChanged }: { user: UserItem; onClose: () => void; onChanged: () => void }) {
  const [role, setRole] = useState(user.role);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await apiPut(`/api/users/${user.id}/role`, { role });
      onChanged();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "修改失败");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ModalWrapper onClose={onClose} title={`修改角色 — ${user.display_name}`}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBox message={error} />}
        <FormField label="角色">
          <select value={role} onChange={(e) => setRole(e.target.value)} className="form-input" autoFocus>
            {ROLE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </FormField>
        <ModalActions onClose={onClose} submitting={submitting} label="保存" />
      </form>
    </ModalWrapper>
  );
}

// ─────── 共用组件 ───────

function ModalWrapper({ onClose, title, children }: { onClose: () => void; title: string; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl border border-slate-200/60 w-full max-w-[400px] mx-4 p-6">
        <h2 className="text-base font-semibold text-slate-800 mb-5">{title}</h2>
        {children}
      </div>
    </div>
  );
}

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-600 mb-1.5">{label}</label>
      {children}
    </div>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="px-3 py-2.5 rounded-lg bg-red-50 border border-red-100 text-sm text-red-600">
      {message}
    </div>
  );
}

function ModalActions({ onClose, submitting, label }: { onClose: () => void; submitting: boolean; label: string }) {
  return (
    <div className="flex gap-3 pt-2">
      <button type="button" onClick={onClose} className="flex-1 py-2.5 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
        取消
      </button>
      <button type="submit" disabled={submitting} className="flex-1 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50">
        {submitting ? "提交中..." : label}
      </button>
    </div>
  );
}
