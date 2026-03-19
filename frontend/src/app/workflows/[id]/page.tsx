"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getWorkflowRun, getWorkflowTrace, retryWorkflow, resumeWorkflow } from "@/lib/api";
import type { WorkflowRun, AgentRunItem } from "@/types";
import { getCaseStatusLabel, getCaseStatusColor, getAgentName } from "@/lib/constants";
import { Badge } from "@/components/ui/Badge";
import { Card, CardTitle } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";

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

  if (loading) return <Spinner label="加载工作流详情..." />;
  if (!run) return (
    <div className="flex flex-col items-center justify-center py-20">
      <p className="text-sm text-slate-500">工作流不存在</p>
    </div>
  );

  return (
    <div className="max-w-5xl mx-auto animate-fade-in">
      <button onClick={() => router.back()} className="text-sm text-slate-500 hover:text-blue-600 transition-colors mb-6 inline-block">
        ← 返回工作流列表
      </button>

      <div className="flex items-center gap-3 mb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">工作流详情 #{run.id}</h1>
        <Badge variant={run.status === "COMPLETED" ? "success" : ["FAILED_RETRYABLE", "FAILED_FINAL"].includes(run.status) ? "danger" : "warning"} size="md" dot>
          {getCaseStatusLabel(run.status)}
        </Badge>
      </div>

      {/* 基本信息 */}
      <Card className="mb-6">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><span className="text-gray-500">案件 ID：</span>#{run.case_id}</div>
          <div><span className="text-gray-500">Graph 版本：</span>{run.graph_version}</div>
          <div><span className="text-slate-500">当前节点：</span>
            {run.current_node ? <Badge variant="muted" size="sm" className="ml-1">{getAgentName(run.current_node)}</Badge> : <span className="text-slate-300">-</span>}
          </div>
          <div><span className="text-slate-500">状态：</span>
            <Badge variant={run.status === "COMPLETED" ? "success" : ["FAILED_RETRYABLE", "FAILED_FINAL"].includes(run.status) ? "danger" : "warning"} size="sm" className="ml-1">
              {getCaseStatusLabel(run.status)}
            </Badge>
          </div>
          <div><span className="text-slate-500">开始时间：</span>{run.started_at || "-"}</div>
          <div><span className="text-slate-500">结束时间：</span>{run.ended_at || "-"}</div>
          <div><span className="text-slate-500">总耗时：</span>{totalLatency}ms</div>
        </div>

        {/* 操作按钮 */}
        {(run.status === "FAILED_RETRYABLE" || run.status === "PAUSED") && (
          <div className="mt-4 flex gap-3">
            {run.status === "FAILED_RETRYABLE" && (
              <button onClick={handleRetry} className="bg-orange-600 text-white px-4 py-2 rounded-lg text-xs font-medium hover:bg-orange-700 transition-colors">
                重试
              </button>
            )}
            {run.status === "PAUSED" && (
              <button onClick={handleResume} className="bg-emerald-600 text-white px-4 py-2 rounded-lg text-xs font-medium hover:bg-emerald-700 transition-colors">
                恢复
              </button>
            )}
          </div>
        )}
      </Card>

      {/* 节点执行时间线 */}
      <Card>
        <CardTitle className="mb-5">执行轨迹</CardTitle>
        {nodes.length === 0 ? (
          <div className="text-sm text-slate-400 text-center py-8">暂无执行记录</div>
        ) : (
          <div className="space-y-3">
            {nodes.map((node, idx) => {
              const isFailed = node.status !== "SUCCESS";
              const barWidth = totalLatency > 0 ? Math.max(((node.latency_ms || 0) / totalLatency) * 100, 5) : 0;
              return (
                <div key={node.id} className={`border rounded-xl p-4 transition-colors ${isFailed ? "border-red-200 bg-red-50/50" : "border-slate-200/80 hover:border-slate-300"}`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2.5">
                      <span className="text-xs text-slate-400 font-mono w-6">{idx + 1}</span>
                      <span className="text-sm font-medium text-slate-800">{getAgentName(node.agent_name)}</span>
                      <Badge variant={isFailed ? "danger" : "success"} size="sm">{node.status}</Badge>
                    </div>
                    <span className="text-sm text-slate-500 tabular-nums">{node.latency_ms || 0}ms</span>
                  </div>
                  {/* 耗时条 */}
                  <div className="w-full bg-slate-100 rounded-full h-1.5">
                    <div
                      className={`h-1.5 rounded-full transition-all ${isFailed ? "bg-red-400" : "bg-blue-400"}`}
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                  <div className="mt-2 text-xs text-slate-400">
                    模型: {node.model_name || "-"} · Prompt v{node.prompt_version || "-"} · Schema v{node.schema_version || "-"}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
