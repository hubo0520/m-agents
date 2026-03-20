"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import {
  getEvalDatasets, getEvalRuns, createEvalDataset, createEvalRun,
  updateEvalDataset, importCasesToDataset,
} from "@/lib/api";
import type { EvalDatasetItem, EvalRunItem } from "@/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";

export default function EvalsPage() {
  const [datasets, setDatasets] = useState<EvalDatasetItem[]>([]);
  const [runs, setRuns] = useState<EvalRunItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDataset, setShowCreateDataset] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  // 数据集编辑
  const [editingDatasetId, setEditingDatasetId] = useState<number | null>(null);
  const [editJsonStr, setEditJsonStr] = useState("");
  const [editSaving, setEditSaving] = useState(false);
  // 从案件导入
  const [showImport, setShowImport] = useState(false);
  const [importName, setImportName] = useState("");
  const [importCaseIds, setImportCaseIds] = useState("");
  // 复用已有结果开关
  const [reuseExisting, setReuseExisting] = useState(true);
  // 轮询
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    const [ds, rs] = await Promise.all([getEvalDatasets(), getEvalRuns()]);
    setDatasets(ds.items || []);
    setRuns(rs.items || []);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 轮询运行中的评测
  useEffect(() => {
    const hasRunning = runs.some((r) => r.status === "RUNNING");
    if (hasRunning && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        const rs = await getEvalRuns();
        setRuns(rs.items || []);
        // 如果没有 RUNNING 的了，停止轮询
        if (!rs.items?.some((r: EvalRunItem) => r.status === "RUNNING")) {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }, 3000);
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [runs]);

  const handleCreateDataset = async () => {
    if (!newName) return;
    const sampleCases = [
      {
        input: { case_id: 1 },
        expected_output: { risk_level: "high", expected_root_causes: ["退货率异常"], expected_action_types: ["advance_settlement"] },
      },
    ];
    await createEvalDataset({ name: newName, description: newDesc, test_cases: sampleCases });
    setNewName("");
    setNewDesc("");
    setShowCreateDataset(false);
    fetchData();
  };

  const handleRunEval = async (datasetId: number) => {
    await createEvalRun({ dataset_id: datasetId, reuse_existing: reuseExisting });
    fetchData();
  };

  const handleEditDataset = async (d: EvalDatasetItem) => {
    if (editingDatasetId === d.id) {
      setEditingDatasetId(null);
      return;
    }
    // 获取数据集详情
    const { getEvalDataset } = await import("@/lib/api");
    const detail = await getEvalDataset(d.id);
    setEditingDatasetId(d.id);
    setEditJsonStr(JSON.stringify(detail.test_cases, null, 2));
  };

  const handleSaveEdit = async () => {
    if (!editingDatasetId) return;
    try {
      const testCases = JSON.parse(editJsonStr);
      setEditSaving(true);
      await updateEvalDataset(editingDatasetId, { test_cases: testCases });
      setEditingDatasetId(null);
      fetchData();
    } catch {
      alert("JSON 格式错误，请检查");
    } finally {
      setEditSaving(false);
    }
  };

  const handleImport = async () => {
    if (!importName || !importCaseIds) return;
    const caseIds = importCaseIds.split(",").map((s) => parseInt(s.trim())).filter((n) => !isNaN(n));
    if (caseIds.length === 0) {
      alert("请输入有效的案件 ID");
      return;
    }
    await importCasesToDataset({ case_ids: caseIds, dataset_name: importName });
    setShowImport(false);
    setImportName("");
    setImportCaseIds("");
    fetchData();
  };

  if (loading) return <Spinner label="加载评测数据..." />;

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="评测中心"
        description="管理评测数据集，使用真实 Agent 工作流 + LLM-as-Judge 评测"
      />

      {/* 评测数据集 */}
      <div className="mb-10">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-slate-800">评测数据集</h2>
          <div className="flex gap-2">
            <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={reuseExisting}
                onChange={(e) => setReuseExisting(e.target.checked)}
                className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              复用已有分析结果
            </label>
            <button
              onClick={() => setShowImport(!showImport)}
              className="border border-blue-200 text-blue-600 px-4 py-2 rounded-lg text-xs font-medium hover:bg-blue-50 transition-colors"
            >
              从案件导入
            </button>
            <button
              onClick={() => setShowCreateDataset(!showCreateDataset)}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-xs font-medium hover:bg-blue-700 transition-colors"
            >
              创建数据集
            </button>
          </div>
        </div>

        {/* 从案件导入面板 */}
        {showImport && (
          <Card className="mb-5">
            <div className="space-y-3">
              <input
                className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm hover:border-slate-300 placeholder:text-slate-300"
                placeholder="数据集名称"
                value={importName}
                onChange={(e) => setImportName(e.target.value)}
              />
              <input
                className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm hover:border-slate-300 placeholder:text-slate-300"
                placeholder="案件 ID（逗号分隔，如：1,2,5）"
                value={importCaseIds}
                onChange={(e) => setImportCaseIds(e.target.value)}
              />
              <div className="flex gap-2">
                <button
                  onClick={handleImport}
                  className="bg-emerald-600 text-white px-4 py-2 rounded-lg text-xs font-medium hover:bg-emerald-700 transition-colors"
                >
                  导入
                </button>
                <button
                  onClick={() => setShowImport(false)}
                  className="px-4 py-2 rounded-lg text-xs font-medium text-slate-500 hover:bg-slate-50 border border-slate-200 transition-colors"
                >
                  取消
                </button>
              </div>
            </div>
          </Card>
        )}

        {showCreateDataset && (
          <Card className="mb-5">
            <div className="space-y-3">
              <input
                className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm hover:border-slate-300 placeholder:text-slate-300"
                placeholder="数据集名称"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
              <input
                className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm hover:border-slate-300 placeholder:text-slate-300"
                placeholder="描述（可选）"
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
              />
              <div className="flex gap-2">
                <button
                  onClick={handleCreateDataset}
                  className="bg-emerald-600 text-white px-4 py-2 rounded-lg text-xs font-medium hover:bg-emerald-700 transition-colors"
                >
                  创建
                </button>
                <button
                  onClick={() => setShowCreateDataset(false)}
                  className="px-4 py-2 rounded-lg text-xs font-medium text-slate-500 hover:bg-slate-50 border border-slate-200 transition-colors"
                >
                  取消
                </button>
              </div>
            </div>
          </Card>
        )}

        <Card padding="none" className="overflow-hidden">
          {datasets.length === 0 ? (
            <EmptyState title="暂无评测数据集" description="点击上方按钮创建数据集或从案件导入" />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">ID</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">名称</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">测试案例数</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">创建时间</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">操作</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((d) => (
                  <>
                    <tr key={d.id} className="border-b border-slate-50 table-row-hover">
                      <td className="px-5 py-3.5 font-mono text-xs text-slate-500">#{d.id}</td>
                      <td className="px-5 py-3.5 font-medium text-slate-800">{d.name}</td>
                      <td className="px-5 py-3.5 tabular-nums text-slate-600">{d.test_case_count}</td>
                      <td className="px-5 py-3.5 text-slate-400 text-xs">{d.created_at}</td>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleRunEval(d.id)}
                            className="text-xs px-3 py-1.5 rounded-md text-blue-600 hover:bg-blue-50 font-medium transition-colors"
                          >
                            运行评测
                          </button>
                          <button
                            onClick={() => handleEditDataset(d)}
                            className="text-xs px-3 py-1.5 rounded-md text-slate-500 hover:bg-slate-50 font-medium transition-colors"
                          >
                            {editingDatasetId === d.id ? "收起" : "编辑"}
                          </button>
                        </div>
                      </td>
                    </tr>
                    {editingDatasetId === d.id && (
                      <tr key={`edit-${d.id}`}>
                        <td colSpan={5} className="px-5 py-3">
                          <textarea
                            className="w-full h-48 border border-slate-200 rounded-lg px-3 py-2 text-xs font-mono focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
                            value={editJsonStr}
                            onChange={(e) => setEditJsonStr(e.target.value)}
                          />
                          <div className="flex gap-2 mt-2">
                            <button
                              onClick={handleSaveEdit}
                              disabled={editSaving}
                              className="bg-emerald-600 text-white px-3 py-1.5 rounded-md text-xs font-medium hover:bg-emerald-700 disabled:opacity-50"
                            >
                              {editSaving ? "保存中..." : "保存"}
                            </button>
                            <button
                              onClick={() => setEditingDatasetId(null)}
                              className="px-3 py-1.5 rounded-md text-xs text-slate-500 hover:bg-slate-50 border border-slate-200"
                            >
                              取消
                            </button>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>

      {/* 评测运行结果 */}
      <div>
        <h2 className="text-base font-semibold text-slate-800 mb-5">评测运行</h2>
        <Card padding="none" className="overflow-hidden">
          {runs.length === 0 ? (
            <EmptyState title="暂无评测运行" description="从数据集启动一次评测运行" />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100">
                    <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">ID</th>
                    <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">数据集</th>
                    <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">模型</th>
                    <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">状态</th>
                    <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Judge 评分</th>
                    <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">采纳率</th>
                    <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">幻觉率</th>
                    <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">平均延迟</th>
                    <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">时间</th>
                    <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((r) => (
                    <tr key={r.id} className="border-b border-slate-50 table-row-hover">
                      <td className="px-5 py-3.5 font-mono text-xs text-slate-500">#{r.id}</td>
                      <td className="px-5 py-3.5 text-slate-600">#{r.dataset_id}</td>
                      <td className="px-5 py-3.5 text-slate-600">{r.model_name}</td>
                      <td className="px-5 py-3.5">
                        {r.status === "RUNNING" ? (
                          <div className="flex items-center gap-2">
                            <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden max-w-[80px]">
                              <div
                                className="h-full bg-blue-500 rounded-full transition-all"
                                style={{ width: `${r.total_count > 0 ? (r.completed_count / r.total_count) * 100 : 0}%` }}
                              />
                            </div>
                            <span className="text-xs text-blue-600 font-medium">
                              {r.completed_count}/{r.total_count}
                            </span>
                          </div>
                        ) : (
                          <Badge variant={r.status === "COMPLETED" ? "success" : r.status === "FAILED" ? "danger" : "warning"} size="sm">
                            {r.status === "COMPLETED" ? "已完成" : r.status === "FAILED" ? "失败" : r.status}
                          </Badge>
                        )}
                      </td>
                      <td className="px-5 py-3.5 font-medium tabular-nums">
                        {r.avg_judge_score != null ? (
                          <span className={
                            r.avg_judge_score >= 80 ? "text-emerald-600" :
                            r.avg_judge_score >= 60 ? "text-amber-600" : "text-red-600"
                          }>
                            {r.avg_judge_score.toFixed(1)}
                          </span>
                        ) : "-"}
                      </td>
                      <td className="px-5 py-3.5 tabular-nums text-slate-600">
                        {r.adoption_rate != null ? `${(r.adoption_rate * 100).toFixed(0)}%` : "-"}
                      </td>
                      <td className="px-5 py-3.5 tabular-nums">
                        <span className={(r.hallucination_rate || 0) > 0.1 ? "text-red-600 font-medium" : "text-slate-600"}>
                          {r.hallucination_rate != null ? `${(r.hallucination_rate * 100).toFixed(0)}%` : "-"}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 tabular-nums text-slate-600">
                        {r.avg_latency_ms != null ? `${(r.avg_latency_ms / 1000).toFixed(1)}s` : "-"}
                      </td>
                      <td className="px-5 py-3.5 text-slate-400 text-xs">{r.ended_at || r.started_at}</td>
                      <td className="px-5 py-3.5">
                        {r.status !== "RUNNING" && (
                          <Link
                            href={`/evals/${r.id}`}
                            className="text-xs px-3 py-1.5 rounded-md text-blue-600 hover:bg-blue-50 font-medium transition-colors"
                          >
                            查看详情
                          </Link>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
