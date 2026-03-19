"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getTaskDetail, updateTaskStatus } from "@/lib/api";
import type { ManualReviewTask } from "@/types";

const REVIEW_RESULTS = [
  { value: "confirmed_fraud", label: "确认欺诈" },
  { value: "false_positive", label: "误报" },
  { value: "needs_investigation", label: "需进一步调查" },
  { value: "normal_behavior", label: "正常行为" },
];

export default function ReviewDetailPage() {
  const params = useParams();
  const taskId = Number(params.id);
  const [task, setTask] = useState<ManualReviewTask | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [comment, setComment] = useState("");
  const [reviewResult, setReviewResult] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const data = await getTaskDetail("manual_review", taskId);
        setTask(data as ManualReviewTask);
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
      const commentText = newStatus === "COMPLETED"
        ? `复核结果: ${reviewResult}。${comment}`
        : comment;

      await updateTaskStatus("manual_review", taskId, {
        new_status: newStatus,
        comment: commentText,
        reviewer_id: "operator",
      });
      const data = await getTaskDetail("manual_review", taskId);
      setTask(data as ManualReviewTask);
      setComment("");
      setReviewResult("");
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
    return <div className="text-center py-20 text-slate-500">复核任务不存在</div>;
  }

  const typeLabels: Record<string, string> = {
    return_fraud: "退货欺诈",
    high_risk_mandatory: "高风险强制复核",
    anomaly_review: "异常行为复核",
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* 面包屑 */}
      <div className="flex items-center gap-2 text-sm text-slate-500 mb-6">
        <Link href="/tasks" className="hover:text-blue-600">任务管理</Link>
        <span>/</span>
        <span className="text-slate-800">复核任务 #{task.id}</span>
      </div>

      {/* 状态条 */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-800">👁️ 人工复核任务</h2>
            <p className="text-sm text-slate-500 mt-1">
              案件 #{task.case_id} · {task.merchant_name}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="px-3 py-1 rounded-full text-sm bg-orange-100 text-orange-700">
              {typeLabels[task.task_type_detail] || task.task_type_detail}
            </span>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              task.status === "PENDING" ? "bg-amber-100 text-amber-700" :
              task.status === "IN_PROGRESS" ? "bg-blue-100 text-blue-700" :
              task.status === "COMPLETED" ? "bg-green-100 text-green-700" :
              "bg-gray-100 text-gray-500"
            }`}>
              {task.status}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* 复核信息 */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-700 mb-4">📋 复核信息</h3>
          <div className="space-y-3 text-sm">
            <div>
              <span className="text-slate-500">复核原因</span>
              <p className="mt-1 text-slate-800 bg-slate-50 rounded-lg p-3">
                {task.review_reason || "无"}
              </p>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">负责人</span>
              <span className="text-slate-700">
                {task.assigned_to === "unassigned" ? "未分配" : task.assigned_to}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">风险等级</span>
              <span className={`px-2 py-0.5 rounded text-xs ${
                task.case_risk_level === "high" ? "bg-red-100 text-red-700" :
                task.case_risk_level === "medium" ? "bg-amber-100 text-amber-700" :
                "bg-green-100 text-green-700"
              }`}>
                {task.case_risk_level || "unknown"}
              </span>
            </div>
          </div>
        </div>

        {/* 关联证据 */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-700 mb-4">📎 关联证据</h3>
          {task.evidence_ids && task.evidence_ids.length > 0 ? (
            <div className="space-y-2">
              {task.evidence_ids.map((evId: number) => (
                <div key={evId} className="flex items-center gap-2 py-1.5 border-b border-slate-100 last:border-0">
                  <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded">
                    证据 #{evId}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-400">无关联证据</p>
          )}
        </div>

        {/* 复核结果（如果已完成） */}
        {task.review_result && (
          <div className="bg-white rounded-xl border border-slate-200 p-6 col-span-2">
            <h3 className="text-base font-semibold text-slate-700 mb-4">✅ 复核结果</h3>
            <p className="text-sm text-slate-800 bg-green-50 rounded-lg p-3">
              {task.review_result}
            </p>
            {task.reviewer_comment && (
              <p className="text-sm text-slate-600 mt-2">
                备注: {task.reviewer_comment}
              </p>
            )}
          </div>
        )}
      </div>

      {/* 操作区 */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mt-6">
        <h3 className="text-base font-semibold text-slate-700 mb-4">⚡ 操作</h3>

        {task.status === "IN_PROGRESS" && (
          <div className="mb-4">
            <label className="block text-sm text-slate-600 mb-2">复核结果</label>
            <select
              value={reviewResult}
              onChange={(e) => setReviewResult(e.target.value)}
              className="w-full border border-slate-300 rounded-lg p-2.5 text-sm bg-white"
            >
              <option value="">请选择复核结果...</option>
              {REVIEW_RESULTS.map((r) => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
          </div>
        )}

        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="输入备注..."
          className="w-full border border-slate-300 rounded-lg p-3 text-sm mb-4 resize-none"
          rows={2}
        />
        <div className="flex gap-3">
          {task.status === "PENDING" && (
            <button
              onClick={() => handleStatusChange("IN_PROGRESS")}
              disabled={actionLoading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              领取任务
            </button>
          )}
          {task.status === "IN_PROGRESS" && (
            <button
              onClick={() => handleStatusChange("COMPLETED")}
              disabled={actionLoading || !reviewResult}
              className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50"
            >
              提交复核结果
            </button>
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
