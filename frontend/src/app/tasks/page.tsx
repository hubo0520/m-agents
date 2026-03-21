"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { getTasks } from "@/lib/api";
import { getTaskStatusLabel, getTaskStatusColor } from "@/lib/constants";
import { PageHeader } from "@/components/ui/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import type { UnifiedTask, PaginatedResponse } from "@/types";

/* 状态分组 */
const STATUS_GROUPS = {
  pending: {
    label: "待处理",
    color: "border-amber-200/80",
    headerBg: "bg-amber-50",
    headerText: "text-amber-800",
    dotColor: "bg-amber-400",
    statuses: ["DRAFT", "PENDING_REVIEW", "PENDING"],
  },
  in_progress: {
    label: "处理中",
    color: "border-blue-200/80",
    headerBg: "bg-blue-50",
    headerText: "text-blue-800",
    dotColor: "bg-blue-400",
    statuses: ["IN_PROGRESS", "EXECUTING", "APPROVED"],
  },
  done: {
    label: "已完成",
    color: "border-emerald-200/80",
    headerBg: "bg-emerald-50",
    headerText: "text-emerald-800",
    dotColor: "bg-emerald-400",
    statuses: ["COMPLETED", "CLOSED", "REJECTED"],
  },
};

const TYPE_INFO: Record<string, { label: string; icon: string; variant: "info" | "success" | "warning" }> = {
  financing: { label: "融资申请", icon: "💰", variant: "info" },
  claim: { label: "理赔申请", icon: "🛡️", variant: "success" },
  manual_review: { label: "人工复核", icon: "👁️", variant: "warning" },
};

function TaskCard({ task }: { task: UnifiedTask }) {
  const typeInfo = TYPE_INFO[task.task_type] || { label: task.task_type, icon: "📋", variant: "muted" as const };

  const detailPath =
    task.task_type === "financing"
      ? `/tasks/financing/${task.task_id}`
      : task.task_type === "claim"
        ? `/tasks/claims/${task.task_id}`
        : `/tasks/reviews/${task.task_id}`;

  return (
    <Link href={detailPath}>
      <div className="bg-white rounded-xl border border-slate-200/80 p-4 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 cursor-pointer group">
        <div className="flex items-center justify-between mb-3">
          <Badge variant={typeInfo.variant} size="sm">
            {typeInfo.icon} {typeInfo.label}
          </Badge>
          <Badge variant="muted" size="sm">
            {getTaskStatusLabel(task.status)}
          </Badge>
        </div>
        <h4 className="text-sm font-medium text-slate-800 mb-2 group-hover:text-slate-900">{task.merchant_name}</h4>
        <div className="text-xs text-slate-400 space-y-1">
          {task.amount !== null && (
            <p className="text-slate-600 font-medium">¥{task.amount.toLocaleString()}</p>
          )}
          <div className="flex items-center justify-between">
            <span>案件 #{task.case_id}</span>
            {task.assigned_to && task.assigned_to !== "unassigned" && (
              <span className="text-slate-500">{task.assigned_to}</span>
            )}
          </div>
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
    const interval = setInterval(fetchTasks, 30000);
    return () => clearInterval(interval);
  }, [fetchTasks]);

  const groupedTasks = Object.entries(STATUS_GROUPS).map(([key, group]) => ({
    key,
    ...group,
    tasks: tasks.filter((t) => group.statuses.includes(t.status)),
  }));

  if (loading) return <Spinner label="加载任务数据..." />;

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="任务管理"
        description={`共 ${tasks.length} 条任务`}
        actions={
          <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white w-full sm:min-w-[120px] hover:border-slate-300"
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
              placeholder="按负责人筛选..."
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white w-full sm:w-40 hover:border-slate-300 placeholder:text-slate-300"
            />
          </div>
        }
      />

      {/* 看板 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {groupedTasks.map((group) => (
          <div key={group.key} className={`rounded-xl border ${group.color} bg-slate-50/50 min-h-[400px]`}>
            <div className={`px-4 py-3 rounded-t-xl ${group.headerBg} flex items-center justify-between`}>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${group.dotColor}`} />
                <span className={`font-semibold text-sm ${group.headerText}`}>{group.label}</span>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full bg-white/60 ${group.headerText} font-medium`}>
                {group.tasks.length}
              </span>
            </div>
            <div className="p-3 space-y-3">
              {group.tasks.length === 0 ? (
                <div className="text-center py-10">
                  <p className="text-sm text-slate-400">暂无任务</p>
                </div>
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
