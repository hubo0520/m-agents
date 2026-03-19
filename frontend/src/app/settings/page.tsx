"use client";

import { useEffect, useState } from "react";
import {
  getAgentConfigs, getPromptVersions, createPromptVersion,
} from "@/lib/api";
import { getAgentName } from "@/lib/constants";
import type { AgentConfig, PromptVersionItem } from "@/types";

const TABS = ["Prompt 版本", "Schema 版本", "模型策略", "工具配置", "审批规则"];

export default function SettingsPage() {
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

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">规则与模型中心</h1>

      {/* Tab 栏 */}
      <div className="flex border-b mb-6">
        {TABS.map((tab, i) => (
          <button
            key={tab}
            onClick={() => setActiveTab(i)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              activeTab === i ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab 内容 */}
      {activeTab === 0 && (
        <div>
          <div className="flex gap-4 mb-4">
            <select
              className="border rounded px-3 py-2 text-sm"
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
            >
              <option value="">全部 Agent</option>
              {configs.map((c) => (
                <option key={c.agent_name} value={c.agent_name}>{getAgentName(c.agent_name)}</option>
              ))}
            </select>
          </div>

          {/* Prompt 版本列表 */}
          <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left">Agent</th>
                  <th className="px-4 py-3 text-left">版本</th>
                  <th className="px-4 py-3 text-left">状态</th>
                  <th className="px-4 py-3 text-left">灰度权重</th>
                  <th className="px-4 py-3 text-left">创建时间</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {promptVersions.map((v) => (
                  <tr key={v.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">{getAgentName(v.agent_name)}</td>
                    <td className="px-4 py-3">v{v.version}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        v.status === "ACTIVE" ? "bg-green-100 text-green-800" :
                        v.status === "DRAFT" ? "bg-yellow-100 text-yellow-800" :
                        "bg-gray-100 text-gray-800"
                      }`}>{v.status}</span>
                    </td>
                    <td className="px-4 py-3">{v.canary_weight || 0}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{v.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 创建新版本 */}
          {selectedAgent && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-3">创建新 Prompt 版本 ({getAgentName(selectedAgent)})</h3>
              <textarea
                className="w-full border rounded p-3 text-sm mb-4"
                rows={5}
                placeholder="输入 Prompt 内容..."
                value={newPrompt}
                onChange={(e) => setNewPrompt(e.target.value)}
              />
              <button
                onClick={handleCreatePrompt}
                className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700"
              >
                创建版本
              </button>
            </div>
          )}
        </div>
      )}

      {activeTab === 1 && (
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-500 text-sm">Schema 版本管理 — 请通过 API 管理 Schema 版本。</p>
        </div>
      )}

      {activeTab === 2 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-3">Agent 模型配置</h3>
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left">Agent</th>
                <th className="px-4 py-3 text-left">活跃 Prompt</th>
                <th className="px-4 py-3 text-left">最新 Schema</th>
                <th className="px-4 py-3 text-left">模型</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {configs.map((c) => (
                <tr key={c.agent_name} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{getAgentName(c.agent_name)}</td>
                  <td className="px-4 py-3">{c.active_prompt_version ? `v${c.active_prompt_version}` : "-"}</td>
                  <td className="px-4 py-3">{c.latest_schema_version ? `v${c.latest_schema_version}` : "-"}</td>
                  <td className="px-4 py-3">{c.model_name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 3 && (
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-500 text-sm">工具配置管理 — 可通过 API 管理工具 allowlist 和审批策略。</p>
        </div>
      )}

      {activeTab === 4 && (
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-500 text-sm">审批规则管理 — 可通过 API 配置各类动作的审批要求和 SLA 时间。</p>
        </div>
      )}
    </div>
  );
}
