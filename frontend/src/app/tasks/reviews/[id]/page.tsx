"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getTaskDetail, updateTaskStatus } from "@/lib/api";
import { Card, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
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
    return <Spinner label="加载复核详情..." />;
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
    <div className="max-w-4xl mx-auto animate-fade-in">
      {/* 面包屑 */}
      <div className="flex items-center gap-2 text-sm text-slate-500 mb-6">
        <Link href="/tasks" className="hover:text-blue-600 transition-colors">任务管理</Link>
        <span className="text-slate-300">/</span>
        <span className="text-slate-800 font-medium">复核任务 #{task.id}</span>
      </div>

      {/* 状态条 */}
      <Card className="mb-6">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-xl font-semibold text-slate-800">👁️ 人工复核任务</h2>
            <p className="text-sm text-slate-500 mt-1">
              案件 #{task.case_id} · {task.merchant_name}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="warning" size="md">
              {typeLabels[task.task_type_detail] || task.task_type_detail}
            </Badge>
            <Badge
              variant={task.status === "COMPLETED" ? "success" : task.status === "IN_PROGRESS" ? "info" : "warning"}
              size="md"
              dot
            >
              {task.status === "PENDING" ? "待处理" : task.status === "IN_PROGRESS" ? "处理中" : task.status === "COMPLETED" ? "已完成" : task.status}
            </Badge>
          </div>
        </div>
      </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* 复核信息 */}
        <Card>
          <CardTitle className="mb-4">📋 复核信息</CardTitle>
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
              <Badge variant={task.case_risk_level === "high" ? "danger" : task.case_risk_level === "medium" ? "warning" : "success"} size="sm">
                {task.case_risk_level || "unknown"}
              </Badge>
            </div>
          </div>
        </Card>

        {/* 关联证据 */}
        <Card>
          <CardTitle className="mb-4">📎 关联证据</CardTitle>
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
        </Card>

        {/* 复核结果（如果已完成） */}
        {task.review_result && (
          <Card className="md:col-span-2">
            <CardTitle className="mb-4">✅ 复核结果</CardTitle>
            <p className="text-sm text-slate-800 bg-green-50 rounded-lg p-3">
              {task.review_result}
            </p>
            {task.reviewer_comment && (
              <p className="text-sm text-slate-600 mt-2">
                备注: {task.reviewer_comment}
              </p>
            )}
          </Card>
        )}
      </div>

      {/* 操作区 */}
      <Card className="mt-5">
        <CardTitle className="mb-4">⚡ 操作</CardTitle>

        {task.status === "IN_PROGRESS" && (
          <div className="mb-4">
            <label className="block text-sm text-slate-600 mb-2">复核结果</label>
            <select
              value={reviewResult}
              onChange={(e) => setReviewResult(e.target.value)}
              className="w-full border border-slate-200 rounded-lg p-2.5 text-sm bg-white hover:border-slate-300"
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
          className="w-full border border-slate-200 rounded-lg p-3 text-sm mb-4 resize-none hover:border-slate-300 placeholder:text-slate-300"
          rows={2}
        />
        <div className="flex gap-3">
          {task.status === "PENDING" && (
            <button
              onClick={() => handleStatusChange("IN_PROGRESS")}
              disabled={actionLoading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40 transition-colors"
            >
              {actionLoading ? "处理中..." : "领取任务"}
            </button>
          )}
          {task.status === "IN_PROGRESS" && (
            <button
              onClick={() => handleStatusChange("COMPLETED")}
              disabled={actionLoading || !reviewResult}
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-40 transition-colors"
            >
              {actionLoading ? "处理中..." : "提交复核结果"}
            </button>
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
