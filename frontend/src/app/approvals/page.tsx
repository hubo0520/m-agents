"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getApprovals, batchApprove } from "@/lib/api";
import { getRoleName } from "@/lib/constants";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import type { ApprovalTask } from "@/types";

const STATUS_MAP: Record<string, { label: string; variant: "warning" | "success" | "danger" | "muted" }> = {
  PENDING:  { label: "待审批", variant: "warning" },
  APPROVED: { label: "已批准", variant: "success" },
  REJECTED: { label: "已驳回", variant: "danger" },
  OVERDUE:  { label: "已超时", variant: "danger" },
};

const TYPE_LABELS: Record<string, string> = {
  business_loan: "经营贷",
  advance_settlement: "回款加速",
  fraud_review: "反欺诈复核",
  claim_submission: "理赔提交",
  manual_handoff: "人工接管",
};

export default function ApprovalsPage() {
  const [items, setItems] = useState<ApprovalTask[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await getApprovals({
        status: statusFilter || undefined,
        approval_type: typeFilter || undefined,
      });
      setItems(res.items || []);
    } catch {
      console.error("获取审批列表失败");
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, [statusFilter, typeFilter]);

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const handleBatch = async (action: string) => {
    if (selectedIds.length === 0) return;
    await batchApprove({
      approval_ids: selectedIds,
      action,
      reviewer_id: "admin",
      comment: `批量${action === "approve" ? "批准" : "驳回"}`,
    });
    setSelectedIds([]);
    fetchData();
  };

  const getSlaRemaining = (dueAt: string | null) => {
    if (!dueAt) return null;
    const due = new Date(dueAt);
    const now = new Date();
    const diff = due.getTime() - now.getTime();
    if (diff <= 0) return "已超时";
    const hours = Math.floor(diff / 3600000);
    const mins = Math.floor((diff % 3600000) / 60000);
    return `${hours}h ${mins}m`;
  };

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="审批中心"
        description="管理和处理所有待审批任务"
        actions={
          selectedIds.length > 0 ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">已选 {selectedIds.length} 项</span>
              <button
                onClick={() => handleBatch("approve")}
                className="bg-emerald-600 text-white px-3.5 py-1.5 rounded-lg text-xs font-medium hover:bg-emerald-700 transition-colors"
              >
                批量批准
              </button>
              <button
                onClick={() => handleBatch("reject")}
                className="bg-red-600 text-white px-3.5 py-1.5 rounded-lg text-xs font-medium hover:bg-red-700 transition-colors"
              >
                批量驳回
              </button>
            </div>
          ) : undefined
        }
      />

      {/* 筛选栏 */}
      <Card className="mb-6" padding="none">
        <div className="px-5 py-4 flex gap-4">
          <select
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white min-w-[120px] hover:border-slate-300"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">全部状态</option>
            <option value="PENDING">待审批</option>
            <option value="APPROVED">已批准</option>
            <option value="REJECTED">已驳回</option>
            <option value="OVERDUE">已超时</option>
          </select>
          <select
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white min-w-[120px] hover:border-slate-300"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            <option value="">全部类型</option>
            <option value="business_loan">经营贷</option>
            <option value="advance_settlement">回款加速</option>
            <option value="fraud_review">反欺诈复核</option>
            <option value="claim_submission">理赔提交</option>
          </select>
        </div>
      </Card>

      {/* 审批列表 */}
      <Card padding="none" className="overflow-hidden">
        {loading ? (
          <Spinner label="加载审批数据..." />
        ) : items.length === 0 ? (
          <EmptyState title="暂无审批任务" description="当前筛选条件下没有匹配的审批" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="px-5 py-3.5 text-left w-10">
                    <input
                      type="checkbox"
                      className="rounded border-slate-300"
                      onChange={(e) =>
                        setSelectedIds(
                          e.target.checked
                            ? items.filter((i) => i.status === "PENDING" || i.status === "OVERDUE").map((i) => i.id)
                            : []
                        )
                      }
                    />
                  </th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">ID</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">类型</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">案件</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">分配角色</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">状态</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">SLA</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">创建时间</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const st = STATUS_MAP[item.status] || { label: item.status, variant: "muted" as const };
                  const sla = getSlaRemaining(item.due_at);
                  return (
                    <tr key={item.id} className="border-b border-slate-50 table-row-hover">
                      <td className="px-5 py-3.5">
                        {(item.status === "PENDING" || item.status === "OVERDUE") && (
                          <input
                            type="checkbox"
                            className="rounded border-slate-300"
                            checked={selectedIds.includes(item.id)}
                            onChange={() => toggleSelect(item.id)}
                          />
                        )}
                      </td>
                      <td className="px-5 py-3.5 font-mono text-xs text-slate-500">#{item.id}</td>
                      <td className="px-5 py-3.5">
                        <Badge variant="info" size="sm">{TYPE_LABELS[item.approval_type] || item.approval_type}</Badge>
                      </td>
                      <td className="px-5 py-3.5">
                        <Link href={`/cases/${item.case_id}`} className="text-blue-600 hover:text-blue-700 font-medium text-sm">
                          案件 #{item.case_id}
                        </Link>
                      </td>
                      <td className="px-5 py-3.5 text-slate-600 text-sm">{item.assignee_role ? getRoleName(item.assignee_role) : "-"}</td>
                      <td className="px-5 py-3.5">
                        <Badge variant={st.variant} size="sm" dot>{st.label}</Badge>
                      </td>
                      <td className="px-5 py-3.5">
                        {sla && (
                          <span className={`text-xs font-medium ${sla === "已超时" ? "text-red-600" : "text-slate-500"}`}>
                            {sla}
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-slate-400 text-xs">{item.created_at}</td>
                      <td className="px-5 py-3.5">
                        <Link
                          href={`/approvals/${item.id}`}
                          className="text-xs px-3 py-1.5 rounded-md text-blue-600 hover:bg-blue-50 font-medium transition-colors"
                        >
                          查看详情
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
