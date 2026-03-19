"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getWorkflows, retryWorkflow, resumeWorkflow } from "@/lib/api";
import type { WorkflowRun } from "@/types";
import { getCaseStatusLabel, getCaseStatusColor, getAgentName } from "@/lib/constants";



export default function WorkflowsPage() {
  const [items, setItems] = useState<WorkflowRun[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await getWorkflows({
        status: statusFilter || undefined,
      });
      setItems(res.items || []);
    } catch {
      console.error("获取工作流列表失败");
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, [statusFilter]);

  const handleRetry = async (runId: number) => {
    await retryWorkflow(runId);
    fetchData();
  };

  const handleResume = async (runId: number) => {
    await resumeWorkflow(runId);
    fetchData();
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">工作流运行中心</h1>

      <div className="flex gap-4 mb-4">
        <select
          className="border rounded px-3 py-2 text-sm"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">全部状态</option>
          <option value="COMPLETED">已完成</option>
          <option value="PAUSED">已暂停</option>
          <option value="PENDING_APPROVAL">待审批</option>
          <option value="EXECUTING">执行中</option>
          <option value="FAILED_RETRYABLE">失败可重试</option>
          <option value="FAILED_FINAL">最终失败</option>
          <option value="REJECTED">已驳回</option>
        </select>
      </div>

      {loading ? (
        <div className="text-center py-10 text-gray-500">加载中...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-10 text-gray-500">暂无工作流运行记录</div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="px-4 py-3 text-left">ID</th>
                <th className="px-4 py-3 text-left">案件</th>
                <th className="px-4 py-3 text-left">版本</th>
                <th className="px-4 py-3 text-left">状态</th>
                <th className="px-4 py-3 text-left">当前节点</th>
                <th className="px-4 py-3 text-left">开始时间</th>
                <th className="px-4 py-3 text-left">结束时间</th>
                <th className="px-4 py-3 text-left">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((item) => {
                return (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono">#{item.id}</td>
                    <td className="px-4 py-3">
                      <Link href={`/cases/${item.case_id}`} className="text-blue-600 hover:underline">
                        案件 #{item.case_id}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{item.graph_version}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getCaseStatusColor(item.status)}`}>
                        {getCaseStatusLabel(item.status)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs">{item.current_node ? getAgentName(item.current_node) : "-"}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{item.started_at}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{item.ended_at || "-"}</td>
                    <td className="px-4 py-3 space-x-2">
                      <Link href={`/workflows/${item.id}`} className="text-blue-600 hover:underline text-sm">
                        详情
                      </Link>
                      {item.status === "FAILED_RETRYABLE" && (
                        <button onClick={() => handleRetry(item.id)} className="text-orange-600 hover:underline text-sm">
                          重试
                        </button>
                      )}
                      {(item.status === "PAUSED" || item.status === "PENDING_APPROVAL") && (
                        <button onClick={() => handleResume(item.id)} className="text-green-600 hover:underline text-sm">
                          恢复
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
