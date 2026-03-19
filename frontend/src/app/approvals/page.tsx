"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getApprovals, batchApprove } from "@/lib/api";
import { getRoleName } from "@/lib/constants";
import type { ApprovalTask } from "@/types";

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  PENDING: { label: "待审批", color: "bg-yellow-100 text-yellow-800" },
  APPROVED: { label: "已批准", color: "bg-green-100 text-green-800" },
  REJECTED: { label: "已驳回", color: "bg-red-100 text-red-800" },
  OVERDUE: { label: "已超时", color: "bg-orange-100 text-orange-800" },
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
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">审批中心</h1>

      {/* 筛选栏 */}
      <div className="flex gap-4 mb-4">
        <select
          className="border rounded px-3 py-2 text-sm"
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
          className="border rounded px-3 py-2 text-sm"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
        >
          <option value="">全部类型</option>
          <option value="business_loan">经营贷</option>
          <option value="advance_settlement">回款加速</option>
          <option value="fraud_review">反欺诈复核</option>
          <option value="claim_submission">理赔提交</option>
        </select>

        {selectedIds.length > 0 && (
          <div className="flex gap-2 ml-auto">
            <span className="text-sm text-gray-600 self-center">已选 {selectedIds.length} 项</span>
            <button onClick={() => handleBatch("approve")} className="bg-green-600 text-white px-3 py-2 rounded text-sm hover:bg-green-700">
              批量批准
            </button>
            <button onClick={() => handleBatch("reject")} className="bg-red-600 text-white px-3 py-2 rounded text-sm hover:bg-red-700">
              批量驳回
            </button>
          </div>
        )}
      </div>

      {/* 审批列表 */}
      {loading ? (
        <div className="text-center py-10 text-gray-500">加载中...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-10 text-gray-500">暂无审批任务</div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="px-4 py-3 text-left w-10">
                  <input
                    type="checkbox"
                    onChange={(e) =>
                      setSelectedIds(
                        e.target.checked
                          ? items.filter((i) => i.status === "PENDING" || i.status === "OVERDUE").map((i) => i.id)
                          : []
                      )
                    }
                  />
                </th>
                <th className="px-4 py-3 text-left">ID</th>
                <th className="px-4 py-3 text-left">类型</th>
                <th className="px-4 py-3 text-left">案件</th>
                <th className="px-4 py-3 text-left">分配角色</th>
                <th className="px-4 py-3 text-left">状态</th>
                <th className="px-4 py-3 text-left">SLA</th>
                <th className="px-4 py-3 text-left">创建时间</th>
                <th className="px-4 py-3 text-left">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((item) => {
                const st = STATUS_LABELS[item.status] || { label: item.status, color: "bg-gray-100 text-gray-800" };
                const sla = getSlaRemaining(item.due_at);
                return (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      {(item.status === "PENDING" || item.status === "OVERDUE") && (
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(item.id)}
                          onChange={() => toggleSelect(item.id)}
                        />
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono">#{item.id}</td>
                    <td className="px-4 py-3">{TYPE_LABELS[item.approval_type] || item.approval_type}</td>
                    <td className="px-4 py-3">
                      <Link href={`/cases/${item.case_id}`} className="text-blue-600 hover:underline">
                        案件 #{item.case_id}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{item.assignee_role ? getRoleName(item.assignee_role) : "-"}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${st.color}`}>
                        {st.label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {sla && (
                        <span className={sla === "已超时" ? "text-red-600 font-medium" : "text-gray-600"}>
                          {sla}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{item.created_at}</td>
                    <td className="px-4 py-3">
                      <Link href={`/approvals/${item.id}`} className="text-blue-600 hover:underline text-sm">
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
    </div>
  );
}
