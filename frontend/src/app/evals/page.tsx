"use client";

import { useEffect, useState } from "react";
import {
  getEvalDatasets, getEvalRuns, createEvalDataset, createEvalRun,
} from "@/lib/api";
import type { EvalDatasetItem, EvalRunItem } from "@/types";

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
    // 创建一个示例评测数据集
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

  if (loading) return <div className="p-6">加载中...</div>;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">评测中心</h1>

      {/* 评测数据集 */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">评测数据集</h2>
          <button
            onClick={() => setShowCreateDataset(!showCreateDataset)}
            className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700"
          >
            创建数据集
          </button>
        </div>

        {showCreateDataset && (
          <div className="bg-white rounded-lg shadow p-6 mb-4">
            <input
              className="w-full border rounded px-3 py-2 text-sm mb-2"
              placeholder="数据集名称"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <input
              className="w-full border rounded px-3 py-2 text-sm mb-4"
              placeholder="描述（可选）"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
            />
            <button onClick={handleCreateDataset} className="bg-green-600 text-white px-4 py-2 rounded text-sm">
              创建
            </button>
          </div>
        )}

        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left">ID</th>
                <th className="px-4 py-3 text-left">名称</th>
                <th className="px-4 py-3 text-left">测试案例数</th>
                <th className="px-4 py-3 text-left">创建时间</th>
                <th className="px-4 py-3 text-left">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {datasets.map((d) => (
                <tr key={d.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">#{d.id}</td>
                  <td className="px-4 py-3 font-medium">{d.name}</td>
                  <td className="px-4 py-3">{d.test_case_count}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{d.created_at}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleRunEval(d.id)}
                      className="text-blue-600 hover:underline text-sm"
                    >
                      运行评测
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 评测运行结果 */}
      <div>
        <h2 className="text-lg font-semibold mb-4">评测运行</h2>
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left">ID</th>
                <th className="px-4 py-3 text-left">数据集</th>
                <th className="px-4 py-3 text-left">模型</th>
                <th className="px-4 py-3 text-left">状态</th>
                <th className="px-4 py-3 text-left">采纳率</th>
                <th className="px-4 py-3 text-left">幻觉率</th>
                <th className="px-4 py-3 text-left">Schema合格率</th>
                <th className="px-4 py-3 text-left">证据覆盖率</th>
                <th className="px-4 py-3 text-left">时间</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {runs.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">#{r.id}</td>
                  <td className="px-4 py-3">#{r.dataset_id}</td>
                  <td className="px-4 py-3">{r.model_name}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      r.status === "COMPLETED" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"
                    }`}>{r.status}</span>
                  </td>
                  <td className="px-4 py-3 font-medium">{r.adoption_rate != null ? `${(r.adoption_rate * 100).toFixed(0)}%` : "-"}</td>
                  <td className="px-4 py-3">
                    <span className={(r.hallucination_rate || 0) > 0.1 ? "text-red-600 font-medium" : ""}>
                      {r.hallucination_rate != null ? `${(r.hallucination_rate * 100).toFixed(0)}%` : "-"}
                    </span>
                  </td>
                  <td className="px-4 py-3">{r.schema_pass_rate != null ? `${(r.schema_pass_rate * 100).toFixed(0)}%` : "-"}</td>
                  <td className="px-4 py-3">{r.evidence_coverage_rate != null ? `${(r.evidence_coverage_rate * 100).toFixed(0)}%` : "-"}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{r.ended_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
