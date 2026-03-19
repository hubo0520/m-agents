"use client";

import { useEffect, useState } from "react";
import {
  getEvalDatasets, getEvalRuns, createEvalDataset, createEvalRun,
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

  const fetchData = async () => {
    setLoading(true);
    const [ds, rs] = await Promise.all([getEvalDatasets(), getEvalRuns()]);
    setDatasets(ds.items || []);
    setRuns(rs.items || []);
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateDataset = async () => {
    if (!newName) return;
    const sampleCases = [
      {
        input: { merchant_id: 1001, risk_type: "cash_gap" },
        expected_output: { risk_level: "high", recommendations: [{ action_type: "advance_settlement" }] },
      },
      {
        input: { merchant_id: 1002, risk_type: "suspected_fraud" },
        expected_output: { risk_level: "critical", recommendations: [{ action_type: "anomaly_review" }] },
      },
    ];
    await createEvalDataset({ name: newName, description: newDesc, test_cases: sampleCases });
    setNewName("");
    setNewDesc("");
    setShowCreateDataset(false);
    fetchData();
  };

  const handleRunEval = async (datasetId: number) => {
    await createEvalRun({ dataset_id: datasetId });
    fetchData();
  };

  if (loading) return <Spinner label="加载评测数据..." />;

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="评测中心"
        description="管理评测数据集，对比不同模型版本的表现"
      />

      {/* 评测数据集 */}
      <div className="mb-10">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-slate-800">评测数据集</h2>
          <button
            onClick={() => setShowCreateDataset(!showCreateDataset)}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-xs font-medium hover:bg-blue-700 transition-colors"
          >
            创建数据集
          </button>
        </div>

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
            <EmptyState title="暂无评测数据集" description="点击上方按钮创建第一个数据集" />
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
                  <tr key={d.id} className="border-b border-slate-50 table-row-hover">
                    <td className="px-5 py-3.5 font-mono text-xs text-slate-500">#{d.id}</td>
                    <td className="px-5 py-3.5 font-medium text-slate-800">{d.name}</td>
                    <td className="px-5 py-3.5 tabular-nums text-slate-600">{d.test_case_count}</td>
                    <td className="px-5 py-3.5 text-slate-400 text-xs">{d.created_at}</td>
                    <td className="px-5 py-3.5">
                      <button
                        onClick={() => handleRunEval(d.id)}
                        className="text-xs px-3 py-1.5 rounded-md text-blue-600 hover:bg-blue-50 font-medium transition-colors"
                      >
                        运行评测
                      </button>
                    </td>
                  </tr>
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
                    <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">采纳率</th>
                    <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">幻觉率</th>
                    <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Schema 合格率</th>
                    <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">证据覆盖率</th>
                    <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">时间</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((r) => (
                    <tr key={r.id} className="border-b border-slate-50 table-row-hover">
                      <td className="px-5 py-3.5 font-mono text-xs text-slate-500">#{r.id}</td>
                      <td className="px-5 py-3.5 text-slate-600">#{r.dataset_id}</td>
                      <td className="px-5 py-3.5 text-slate-600">{r.model_name}</td>
                      <td className="px-5 py-3.5">
                        <Badge variant={r.status === "COMPLETED" ? "success" : "warning"} size="sm">
                          {r.status}
                        </Badge>
                      </td>
                      <td className="px-5 py-3.5 font-medium tabular-nums">
                        {r.adoption_rate != null ? `${(r.adoption_rate * 100).toFixed(0)}%` : "-"}
                      </td>
                      <td className="px-5 py-3.5 tabular-nums">
                        <span className={(r.hallucination_rate || 0) > 0.1 ? "text-red-600 font-medium" : "text-slate-600"}>
                          {r.hallucination_rate != null ? `${(r.hallucination_rate * 100).toFixed(0)}%` : "-"}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 tabular-nums text-slate-600">
                        {r.schema_pass_rate != null ? `${(r.schema_pass_rate * 100).toFixed(0)}%` : "-"}
                      </td>
                      <td className="px-5 py-3.5 tabular-nums text-slate-600">
                        {r.evidence_coverage_rate != null ? `${(r.evidence_coverage_rate * 100).toFixed(0)}%` : "-"}
                      </td>
                      <td className="px-5 py-3.5 text-slate-400 text-xs">{r.ended_at}</td>
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
