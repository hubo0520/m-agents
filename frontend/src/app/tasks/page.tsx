"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { getTasks } from "@/lib/api";
import { getTaskStatusLabel, getTaskStatusColor } from "@/lib/constants";
import type { UnifiedTask, PaginatedResponse } from "@/types";

/* 状态分组 */
const STATUS_GROUPS = {
  pending: {
    label: "待处理",
    color: "bg-amber-50 border-amber-200",
    headerColor: "bg-amber-100 text-amber-800",
    statuses: ["DRAFT", "PENDING_REVIEW", "PENDING"],
  },
  in_progress: {
    label: "处理中",
    color: "bg-blue-50 border-blue-200",
    headerColor: "bg-blue-100 text-blue-800",
    statuses: ["IN_PROGRESS", "EXECUTING", "APPROVED"],
  },
  done: {
    label: "已完成",
    color: "bg-green-50 border-green-200",
    headerColor: "bg-green-100 text-green-800",
    statuses: ["COMPLETED", "CLOSED", "REJECTED"],
  },
};

const TYPE_LABELS: Record<string, { label: string; icon: string; color: string }> = {
  financing: { label: "融资申请", icon: "💰", color: "bg-purple-100 text-purple-700" },
  claim: { label: "理赔申请", icon: "🛡️", color: "bg-teal-100 text-teal-700" },
  manual_review: { label: "人工复核", icon: "👁️", color: "bg-orange-100 text-orange-700" },
};

const STATUS_LABELS: Record<string, { label: string; color: string }> = {};

function TaskCard({ task }: { task: UnifiedTask }) {
  const typeInfo = TYPE_LABELS[task.task_type] || { label: task.task_type, icon: "📋", color: "bg-gray-100" };
  const statusInfo = STATUS_LABELS[task.status] || { label: getTaskStatusLabel(task.status), color: getTaskStatusColor(task.status) };

  const detailPath =
    task.task_type === "financing"
      ? `/tasks/financing/${task.task_id}`
      : task.task_type === "claim"
        ? `/tasks/claims/${task.task_id}`
        : `/tasks/reviews/${task.task_id}`;

  return (
    <Link href={detailPath}>
      <div className="bg-white rounded-lg border border-slate-200 p-4 hover:shadow-md transition-shadow cursor-pointer">
        <div className="flex items-center justify-between mb-2">
          <span className={`text-xs px-2 py-0.5 rounded-full ${typeInfo.color}`}>
            {typeInfo.icon} {typeInfo.label}
          </span>
          <span className={`text-xs px-2 py-0.5 rounded-full ${statusInfo.color}`}>
            {statusInfo.label}
          </span>
        </div>
        <h4 className="text-sm font-medium text-slate-800 mb-1">{task.merchant_name}</h4>
        <div className="text-xs text-slate-500 space-y-0.5">
          {task.amount !== null && (
            <p>金额: ¥{task.amount.toLocaleString()}</p>
          )}
          {task.assigned_to && task.assigned_to !== "unassigned" && (
            <p>负责人: {task.assigned_to}</p>
          )}
          <p>案件 #{task.case_id}</p>
          {task.created_at && (
            <p>{new Date(task.created_at).toLocaleDateString("zh-CN")}</p>
          )}
        </div>
      </div>
    </Link>
  );
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<UnifiedTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState("");
  const [filterAssignee, setFilterAssignee] = useState("");

  const fetchTasks = useCallback(async () => {
    try {
      const res: PaginatedResponse<UnifiedTask> = await getTasks({
        task_type: filterType || undefined,
        assigned_to: filterAssignee || undefined,
        page_size: 100,
      });
      setTasks(res.items);
    } catch (e) {
      console.error("获取任务失败:", e);
    } finally {
      setLoading(false);
    }
  }, [filterType, filterAssignee]);

  useEffect(() => {
    fetchTasks();
    // 30秒自动刷新
    const interval = setInterval(fetchTasks, 30000);
    return () => clearInterval(interval);
  }, [fetchTasks]);

  const groupedTasks = Object.entries(STATUS_GROUPS).map(([key, group]) => ({
    key,
    ...group,
    tasks: tasks.filter((t) => group.statuses.includes(t.status)),
  }));

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">📋 任务管理</h2>
          <p className="text-sm text-slate-500 mt-1">共 {tasks.length} 条任务</p>
        </div>

        {/* 筛选栏 */}
        <div className="flex gap-3">
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm bg-white"
          >
            <option value="">全部类型</option>
            <option value="financing">💰 融资申请</option>
            <option value="claim">🛡️ 理赔申请</option>
            <option value="manual_review">👁️ 人工复核</option>
          </select>
          <input
            type="text"
            value={filterAssignee}
            onChange={(e) => setFilterAssignee(e.target.value)}
            placeholder="按负责人筛选"
            className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm bg-white w-40"
          />
        </div>
      </div>

      {/* 看板 */}
      <div className="grid grid-cols-3 gap-6">
        {groupedTasks.map((group) => (
          <div key={group.key} className={`rounded-xl border ${group.color} min-h-[400px]`}>
            <div className={`px-4 py-3 rounded-t-xl ${group.headerColor} flex items-center justify-between`}>
              <span className="font-semibold text-sm">{group.label}</span>
              <span className="text-xs bg-white/60 px-2 py-0.5 rounded-full">
                {group.tasks.length}
              </span>
            </div>
            <div className="p-3 space-y-3">
              {group.tasks.length === 0 ? (
                <p className="text-center text-sm text-slate-400 py-8">暂无任务</p>
              ) : (
                group.tasks.map((task) => (
                  <TaskCard key={`${task.task_type}-${task.task_id}`} task={task} />
                ))
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
