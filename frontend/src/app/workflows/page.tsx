"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getWorkflows, retryWorkflow, resumeWorkflow } from "@/lib/api";
import type { WorkflowRun } from "@/types";
import { getCaseStatusLabel, getCaseStatusColor, getAgentName } from "@/lib/constants";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";

const getStatusVariant = (status: string) => {
  if (["COMPLETED"].includes(status)) return "success";
  if (["PENDING_APPROVAL", "PAUSED"].includes(status)) return "warning";
  if (["FAILED_RETRYABLE", "FAILED_FINAL", "REJECTED"].includes(status)) return "danger";
  if (["EXECUTING"].includes(status)) return "info";
  return "default";
};

export default function WorkflowsPage() {
  const [items, setItems] = useState<WorkflowRun[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await getWorkflows({ status: statusFilter || undefined });
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
    <div className="animate-fade-in">
      <PageHeader
        title="工作流运行中心"
        description="监控和管理所有工作流执行实例"
      />

      {/* 筛选栏 */}
      <Card className="mb-6" padding="none">
        <div className="px-5 py-4 flex gap-4">
          <select
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white min-w-[140px] hover:border-slate-300"
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
      </Card>

      {/* 工作流列表 */}
      <Card padding="none" className="overflow-hidden">
        {loading ? (
          <Spinner label="加载工作流数据..." />
        ) : items.length === 0 ? (
          <EmptyState title="暂无工作流运行记录" description="当前筛选条件下没有匹配的工作流" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">ID</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">案件</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">版本</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">状态</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">当前节点</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">开始时间</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">结束时间</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-b border-slate-50 table-row-hover">
                    <td className="px-5 py-3.5 font-mono text-xs text-slate-500">#{item.id}</td>
                    <td className="px-5 py-3.5">
                      <Link href={`/cases/${item.case_id}`} className="text-blue-600 hover:text-blue-700 font-medium text-sm">
                        案件 #{item.case_id}
                      </Link>
                    </td>
                    <td className="px-5 py-3.5 text-slate-400 text-xs">{item.graph_version}</td>
                    <td className="px-5 py-3.5">
                      <Badge variant={getStatusVariant(item.status) as any} size="sm" dot>
                        {getCaseStatusLabel(item.status)}
                      </Badge>
                    </td>
                    <td className="px-5 py-3.5">
                      {item.current_node ? (
                        <Badge variant="muted" size="sm">{getAgentName(item.current_node)}</Badge>
                      ) : (
                        <span className="text-slate-300">-</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-slate-400 text-xs">{item.started_at}</td>
                    <td className="px-5 py-3.5 text-slate-400 text-xs">{item.ended_at || "-"}</td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-1">
                        <Link
                          href={`/workflows/${item.id}`}
                          className="text-xs px-2.5 py-1.5 rounded-md text-blue-600 hover:bg-blue-50 font-medium transition-colors"
                        >
                          详情
                        </Link>
                        {item.status === "FAILED_RETRYABLE" && (
                          <button
                            onClick={() => handleRetry(item.id)}
                            className="text-xs px-2.5 py-1.5 rounded-md text-orange-600 hover:bg-orange-50 font-medium transition-colors"
                          >
                            重试
                          </button>
                        )}
                        {(item.status === "PAUSED" || item.status === "PENDING_APPROVAL") && (
                          <button
                            onClick={() => handleResume(item.id)}
                            className="text-xs px-2.5 py-1.5 rounded-md text-emerald-600 hover:bg-emerald-50 font-medium transition-colors"
                          >
                            恢复
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
