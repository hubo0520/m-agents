"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getTaskDetail, updateTaskStatus } from "@/lib/api";
import { getTaskStatusLabel, getTaskStatusColor, getEvidenceTypeLabel, formatEvidenceSummary } from "@/lib/constants";
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
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (!task) {
    return <div className="text-center py-20 text-slate-500">理赔申请不存在</div>;
  }

  const returnDetails = task.return_details;

  return (
    <div className="max-w-4xl mx-auto">
      {/* 面包屑 */}
      <div className="flex items-center gap-2 text-sm text-slate-500 mb-6">
        <Link href="/tasks" className="hover:text-blue-600">任务管理</Link>
        <span>/</span>
        <span className="text-slate-800">理赔申请 #{task.id}</span>
      </div>

      {/* 状态条 */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-800">🛡️ 理赔申请草稿</h2>
            <p className="text-sm text-slate-500 mt-1">
              案件 #{task.case_id} · {task.merchant_name}
            </p>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getTaskStatusColor(task.claim_status)}`}>
            {getTaskStatusLabel(task.claim_status)}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* 理赔信息 */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-700 mb-4">💵 理赔信息</h3>
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
        </div>

        {/* 退货详情 */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-700 mb-4">📦 退货详情</h3>
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
        </div>

        {/* 证据列表 */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 col-span-2">
          <h3 className="text-base font-semibold text-slate-700 mb-4">📎 关联证据</h3>
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
        </div>
      </div>

      {/* 操作区 */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mt-6">
        <h3 className="text-base font-semibold text-slate-700 mb-4">⚡ 操作</h3>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="输入备注..."
          className="w-full border border-slate-300 rounded-lg p-3 text-sm mb-4 resize-none"
          rows={2}
        />
        <div className="flex gap-3">
          {task.claim_status === "DRAFT" && (
            <button
              onClick={() => handleStatusChange("PENDING_REVIEW")}
              disabled={actionLoading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              提交审核
            </button>
          )}
          {task.claim_status === "PENDING_REVIEW" && (
            <>
              <button
                onClick={() => handleStatusChange("APPROVED")}
                disabled={actionLoading}
                className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50"
              >
                审核通过
              </button>
              <button
                onClick={() => handleStatusChange("REJECTED")}
                disabled={actionLoading}
                className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 disabled:opacity-50"
              >
                驳回
              </button>
            </>
          )}
          <Link
            href={`/cases/${task.case_id}`}
            className="px-4 py-2 border border-slate-300 rounded-lg text-sm text-slate-600 hover:bg-slate-50"
          >
            查看关联案件
          </Link>
        </div>
      </div>
    </div>
  );
}
