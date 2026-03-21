"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getTaskDetail, updateTaskStatus } from "@/lib/api";
import { getTaskStatusLabel, getTaskStatusColor, getEvidenceTypeLabel, formatEvidenceSummary } from "@/lib/constants";
import { Card, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import type { ClaimApplication } from "@/types";

export default function ClaimDetailPage() {
  const params = useParams();
  const taskId = Number(params.id);
  const [task, setTask] = useState<ClaimApplication | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [comment, setComment] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const data = await getTaskDetail("claim", taskId);
        setTask(data as ClaimApplication);
      } catch (e) {
        console.error("加载失败:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [taskId]);

  const handleStatusChange = async (newStatus: string) => {
    if (!task) return;
    setActionLoading(true);
    try {
      await updateTaskStatus("claim", taskId, {
        new_status: newStatus,
        comment,
        reviewer_id: "operator",
      });
      const data = await getTaskDetail("claim", taskId);
      setTask(data as ClaimApplication);
      setComment("");
    } catch (e) {
      alert(`操作失败: ${e}`);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return <Spinner label="加载理赔详情..." />;
  }

  if (!task) {
    return <div className="text-center py-20 text-slate-500">理赔申请不存在</div>;
  }

  const returnDetails = task.return_details;

  return (
    <div className="max-w-4xl mx-auto animate-fade-in">
      {/* 面包屑 */}
      <div className="flex items-center gap-2 text-sm text-slate-500 mb-6">
        <Link href="/tasks" className="hover:text-blue-600 transition-colors">任务管理</Link>
        <span className="text-slate-300">/</span>
        <span className="text-slate-800 font-medium">理赔申请 #{task.id}</span>
      </div>

      {/* 状态条 */}
      <Card className="mb-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-xl font-semibold text-slate-800">🛡️ 理赔申请草稿</h2>
            <p className="text-sm text-slate-500 mt-1">
              案件 #{task.case_id} · {task.merchant_name}
            </p>
          </div>
          <Badge variant={task.claim_status === "APPROVED" ? "success" : task.claim_status === "REJECTED" ? "danger" : "warning"} size="md" dot>
            {getTaskStatusLabel(task.claim_status)}
          </Badge>
        </div>
      </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* 理赔信息 */}
        <Card>
          <CardTitle className="mb-4">💵 理赔信息</CardTitle>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-slate-500">理赔金额</span>
              <span className="text-lg font-bold text-teal-600">
                ¥{task.claim_amount?.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-slate-500">理赔原因</span>
              <span className="text-sm text-slate-700 text-right max-w-[200px]">
                {task.claim_reason || "-"}
              </span>
            </div>
            {task.policy_id && (
              <div className="flex justify-between">
                <span className="text-sm text-slate-500">保单 ID</span>
                <span className="text-sm text-slate-700">#{task.policy_id}</span>
              </div>
            )}
          </div>
        </Card>

        {/* 退货详情 */}
        <Card>
          <CardTitle className="mb-4">📦 退货详情</CardTitle>
          {returnDetails ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">退货笔数</span>
                <span>{returnDetails.return_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">退款总额</span>
                <span className="text-red-600">¥{returnDetails.total_refund_amount?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">时间范围</span>
                <span>{returnDetails.period}</span>
              </div>
              {returnDetails.reason_distribution && (
                <div className="mt-3">
                  <p className="text-slate-500 mb-2">退货原因分布:</p>
                  {Object.entries(returnDetails.reason_distribution).map(([reason, count]) => (
                    <div key={reason} className="flex justify-between text-xs py-0.5">
                      <span className="text-slate-600">{reason}</span>
                      <span className="text-slate-800">{count as number} 笔</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-slate-400">无退货数据</p>
          )}
        </Card>

        {/* 证据列表 */}
        <Card className="md:col-span-2">
          <CardTitle className="mb-4">📎 关联证据</CardTitle>
          {task.evidence_snapshot && Array.isArray(task.evidence_snapshot) && task.evidence_snapshot.length > 0 ? (
            <div className="space-y-2">
              {task.evidence_snapshot.map((ev: any, idx: number) => (
                <div key={idx} className="flex items-center gap-3 py-2 border-b border-slate-100 last:border-0">
                  <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                    {getEvidenceTypeLabel(ev.evidence_type)}
                  </span>
<span className="text-sm text-slate-700 flex-1">{formatEvidenceSummary(ev.summary) || "-"}</span>
                  {ev.importance_score && (
                    <span className="text-xs text-slate-400">
                      重要性: {(ev.importance_score * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-400">无证据数据</p>
          )}
        </Card>
      </div>

      {/* 操作区 */}
      <Card className="mt-5">
        <CardTitle className="mb-4">⚡ 操作</CardTitle>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="输入备注..."
          className="w-full border border-slate-200 rounded-lg p-3 text-sm mb-4 resize-none hover:border-slate-300 placeholder:text-slate-300"
          rows={2}
        />
        <div className="flex gap-3">
          {task.claim_status === "DRAFT" && (
            <button
              onClick={() => handleStatusChange("PENDING_REVIEW")}
              disabled={actionLoading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40 transition-colors"
            >
              {actionLoading ? "处理中..." : "提交审核"}
            </button>
          )}
          {task.claim_status === "PENDING_REVIEW" && (
            <>
              <button
                onClick={() => handleStatusChange("APPROVED")}
                disabled={actionLoading}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-40 transition-colors"
              >
                {actionLoading ? "处理中..." : "审核通过"}
              </button>
              <button
                onClick={() => handleStatusChange("REJECTED")}
                disabled={actionLoading}
                className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-40 transition-colors"
              >
                {actionLoading ? "处理中..." : "驳回"}
              </button>
            </>
          )}
          <Link
            href={`/cases/${task.case_id}`}
            className="px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50 hover:border-slate-300 transition-all"
          >
            查看关联案件
          </Link>
        </div>
      </Card>
    </div>
  );
}
