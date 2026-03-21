"use client";

import { useEffect, useState } from "react";
import {
  getAgentConfigs, getPromptVersions, createPromptVersion,
} from "@/lib/api";
import { getAgentName } from "@/lib/constants";
import type { AgentConfig, PromptVersionItem } from "@/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/lib/auth";
import { UserManagementTab } from "@/components/UserManagementTab";

const BASE_TABS = ["Prompt 版本", "Schema 版本", "模型策略", "工具配置", "审批规则"];

export default function SettingsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const TABS = isAdmin ? [...BASE_TABS, "用户管理"] : BASE_TABS;

  const [activeTab, setActiveTab] = useState(0);
  const [configs, setConfigs] = useState<AgentConfig[]>([]);
  const [promptVersions, setPromptVersions] = useState<PromptVersionItem[]>([]);
  const [selectedAgent, setSelectedAgent] = useState("");
  const [newPrompt, setNewPrompt] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAgentConfigs().then((r) => setConfigs(r.configs || [])).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (activeTab === 0) {
      getPromptVersions(selectedAgent || undefined).then((r) => setPromptVersions(r.items || []));
    }
  }, [activeTab, selectedAgent]);

  const handleCreatePrompt = async () => {
    if (!selectedAgent || !newPrompt) return;
    await createPromptVersion({ agent_name: selectedAgent, content: newPrompt });
    setNewPrompt("");
    getPromptVersions(selectedAgent).then((r) => setPromptVersions(r.items || []));
  };

  if (loading) return <Spinner label="加载配置..." />;

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="规则与模型中心"
        description="管理 Agent 配置、Prompt 版本和审批规则"
      />

      {/* Tab 栏 — Segment Control 风格 */}
      <div className="mb-6 sm:mb-8">
        <div className="inline-flex bg-slate-100 rounded-lg p-1 gap-0.5 max-w-full overflow-x-auto">
          {TABS.map((tab, i) => (
            <button
              key={tab}
              onClick={() => setActiveTab(i)}
              className={`px-3 sm:px-4 py-2 text-xs font-medium rounded-md transition-all duration-200 whitespace-nowrap ${
                activeTab === i
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Tab 内容 */}
      {activeTab === 0 && (
        <div className="space-y-6">
          <Card padding="none">
            <div className="px-5 py-4">
              <select
                className="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white min-w-[160px] hover:border-slate-300"
                value={selectedAgent}
                onChange={(e) => setSelectedAgent(e.target.value)}
              >
                <option value="">全部 Agent</option>
                {configs.map((c) => (
                  <option key={c.agent_name} value={c.agent_name}>{getAgentName(c.agent_name)}</option>
                ))}
              </select>
            </div>
          </Card>

          <Card padding="none" className="overflow-hidden">
            <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Agent</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">版本</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">状态</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">灰度权重</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">创建时间</th>
                </tr>
              </thead>
              <tbody>
                {promptVersions.map((v) => (
                  <tr key={v.id} className="border-b border-slate-50 table-row-hover">
                    <td className="px-5 py-3.5 font-medium text-slate-800">{getAgentName(v.agent_name)}</td>
                    <td className="px-5 py-3.5 font-mono text-xs text-slate-600">v{v.version}</td>
                    <td className="px-5 py-3.5">
                      <Badge
                        variant={v.status === "ACTIVE" ? "success" : v.status === "DRAFT" ? "warning" : "muted"}
                        size="sm"
                        dot
                      >
                        {v.status}
                      </Badge>
                    </td>
                    <td className="px-5 py-3.5 tabular-nums text-slate-600">{v.canary_weight || 0}</td>
                    <td className="px-5 py-3.5 text-slate-400 text-xs">{v.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </Card>

          {selectedAgent && (
            <Card>
              <h3 className="text-sm font-semibold text-slate-800 mb-4">
                创建新 Prompt 版本
                <span className="ml-2 text-slate-400 font-normal">({getAgentName(selectedAgent)})</span>
              </h3>
              <textarea
                className="w-full border border-slate-200 rounded-lg p-3 text-sm mb-4 resize-none hover:border-slate-300 placeholder:text-slate-300"
                rows={5}
                placeholder="输入 Prompt 内容..."
                value={newPrompt}
                onChange={(e) => setNewPrompt(e.target.value)}
              />
              <button
                onClick={handleCreatePrompt}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-xs font-medium hover:bg-blue-700 transition-colors disabled:opacity-40"
                disabled={!newPrompt.trim()}
              >
                创建版本
              </button>
            </Card>
          )}
        </div>
      )}

      {activeTab === 1 && (
        <Card>
          <p className="text-sm text-slate-400">Schema 版本管理 — 请通过 API 管理 Schema 版本。</p>
        </Card>
      )}

      {activeTab === 2 && (
        <Card padding="none" className="overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100">
            <h3 className="text-sm font-semibold text-slate-800">Agent 模型配置</h3>
          </div>
          <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Agent</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">活跃 Prompt</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">最新 Schema</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">模型</th>
              </tr>
            </thead>
            <tbody>
              {configs.map((c) => (
                <tr key={c.agent_name} className="border-b border-slate-50 table-row-hover">
                  <td className="px-5 py-3.5 font-medium text-slate-800">{getAgentName(c.agent_name)}</td>
                  <td className="px-5 py-3.5 font-mono text-xs text-slate-600">{c.active_prompt_version ? `v${c.active_prompt_version}` : "-"}</td>
                  <td className="px-5 py-3.5 font-mono text-xs text-slate-600">{c.latest_schema_version ? `v${c.latest_schema_version}` : "-"}</td>
                  <td className="px-5 py-3.5 text-slate-600">{c.model_name}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </Card>
      )}

      {activeTab === 3 && (
        <Card>
          <p className="text-sm text-slate-400">工具配置管理 — 可通过 API 管理工具 allowlist 和审批策略。</p>
        </Card>
      )}

      {activeTab === 4 && (
        <Card>
          <p className="text-sm text-slate-400">审批规则管理 — 可通过 API 配置各类动作的审批要求和 SLA 时间。</p>
        </Card>
      )}

      {isAdmin && activeTab === 5 && (
        <UserManagementTab />
      )}
    </div>
  );
}
