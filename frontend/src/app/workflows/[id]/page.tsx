"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getWorkflowRun, getWorkflowTrace, retryWorkflow, resumeWorkflow } from "@/lib/api";
import type { WorkflowRun, AgentRunItem } from "@/types";
import { getCaseStatusLabel, getCaseStatusColor, getAgentName } from "@/lib/constants";

export default function WorkflowDetailPage() {
  const params = useParams();
  const router = useRouter();
  const runId = Number(params.id);
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [nodes, setNodes] = useState<AgentRunItem[]>([]);
  const [totalLatency, setTotalLatency] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!runId) return;
    Promise.all([
      getWorkflowRun(runId),
      getWorkflowTrace(runId),
    ]).then(([runData, traceData]) => {
      setRun(runData);
      setNodes(traceData.nodes || []);
      setTotalLatency(traceData.total_latency_ms || 0);
    }).finally(() => setLoading(false));
  }, [runId]);

  const handleRetry = async () => {
    await retryWorkflow(runId);
    router.push("/workflows");
  };

  const handleResume = async () => {
    await resumeWorkflow(runId);
    router.push("/workflows");
  };

  if (loading) return <div className="p-6">加载中...</div>;
  if (!run) return <div className="p-6">工作流不存在</div>;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <button onClick={() => router.back()} className="text-blue-600 hover:underline mb-4 text-sm">
        ← 返回工作流列表
      </button>

      <h1 className="text-2xl font-bold mb-6">工作流详情 #{run.id}</h1>

      {/* 基本信息 */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><span className="text-gray-500">案件 ID：</span>#{run.case_id}</div>
          <div><span className="text-gray-500">Graph 版本：</span>{run.graph_version}</div>
          <div><span className="text-gray-500">当前节点：</span>
            <span>{run.current_node ? getAgentName(run.current_node) : "-"}</span>
          </div>
          <div><span className="text-gray-500">状态：</span>
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getCaseStatusColor(run.status)}`}>{getCaseStatusLabel(run.status)}</span>
          </div>
          <div><span className="text-gray-500">开始时间：</span>{run.started_at || "-"}</div>
          <div><span className="text-gray-500">结束时间：</span>{run.ended_at || "-"}</div>
          <div><span className="text-gray-500">总耗时：</span>{totalLatency}ms</div>
        </div>

        {/* 操作按钮 */}
        {(run.status === "FAILED_RETRYABLE" || run.status === "PAUSED") && (
          <div className="mt-4 flex gap-3">
            {run.status === "FAILED_RETRYABLE" && (
              <button onClick={handleRetry} className="bg-orange-600 text-white px-4 py-2 rounded text-sm hover:bg-orange-700">
                重试
              </button>
            )}
            {run.status === "PAUSED" && (
              <button onClick={handleResume} className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700">
                恢复
              </button>
            )}
          </div>
        )}
      </div>

      {/* 节点执行时间线 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">执行轨迹</h2>
        {nodes.length === 0 ? (
          <div className="text-gray-500 text-sm">暂无执行记录</div>
        ) : (
          <div className="space-y-3">
            {nodes.map((node, idx) => {
              const isFailed = node.status !== "SUCCESS";
              const barWidth = totalLatency > 0 ? Math.max(((node.latency_ms || 0) / totalLatency) * 100, 5) : 0;
              return (
                <div key={node.id} className={`border rounded-lg p-4 ${isFailed ? "border-red-300 bg-red-50" : "border-gray-200"}`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400 w-6">{idx + 1}</span>
                      <span className="text-sm font-medium">{getAgentName(node.agent_name)}</span>
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        isFailed ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"
                      }`}>{node.status}</span>
                    </div>
                    <span className="text-sm text-gray-500">{node.latency_ms || 0}ms</span>
                  </div>
                  {/* 耗时条 */}
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${isFailed ? "bg-red-400" : "bg-blue-400"}`}
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                  <div className="mt-1 text-xs text-gray-400">
                    模型: {node.model_name || "-"} · Prompt v{node.prompt_version || "-"} · Schema v{node.schema_version || "-"}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
