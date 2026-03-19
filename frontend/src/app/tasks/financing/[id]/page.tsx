"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getTaskDetail, updateTaskStatus } from "@/lib/api";
import { getTaskStatusLabel, getTaskStatusColor } from "@/lib/constants";
import type { FinancingApplication } from "@/types";

export default function FinancingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = Number(params.id);
  const [task, setTask] = useState<FinancingApplication | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [comment, setComment] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const data = await getTaskDetail("financing", taskId);
        setTask(data as FinancingApplication);
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
      await updateTaskStatus("financing", taskId, {
        new_status: newStatus,
        comment,
        reviewer_id: "operator",
      });
      const data = await getTaskDetail("financing", taskId);
      setTask(data as FinancingApplication);
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
    return <div className="text-center py-20 text-slate-500">融资申请不存在</div>;
  }

  const snapshot = task.merchant_info_snapshot;
  const settlement = task.historical_settlement;
  const plan = task.repayment_plan;

  return (
    <div className="max-w-4xl mx-auto">
      {/* 面包屑 */}
      <div className="flex items-center gap-2 text-sm text-slate-500 mb-6">
        <Link href="/tasks" className="hover:text-blue-600">任务管理</Link>
        <span>/</span>
        <span className="text-slate-800">融资申请 #{task.id}</span>
      </div>

      {/* 状态条 */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-800">💰 融资申请草稿</h2>
            <p className="text-sm text-slate-500 mt-1">
              案件 #{task.case_id} · {task.merchant_name}
            </p>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getTaskStatusColor(task.approval_status)}`}>
            {getTaskStatusLabel(task.approval_status)}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* 资金需求 */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-700 mb-4">💵 资金需求</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-slate-500">申请金额</span>
              <span className="text-lg font-bold text-blue-600">
                ¥{task.amount_requested?.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-slate-500">贷款用途</span>
              <span className="text-sm text-slate-700 text-right max-w-[200px]">
                {task.loan_purpose || "-"}
              </span>
            </div>
          </div>
        </div>

        {/* 商家信息快照 */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-700 mb-4">🏪 商家信息</h3>
          {snapshot ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">行业</span>
                <span>{snapshot.industry}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">店铺等级</span>
                <span>{snapshot.store_level}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">90天销售额</span>
                <span>¥{snapshot.total_sales_90d?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">90天退货额</span>
                <span>¥{snapshot.total_returns_90d?.toLocaleString()}</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400">无快照数据</p>
          )}
        </div>

        {/* 历史回款 */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-700 mb-4">📊 历史回款</h3>
          {settlement ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">回款笔数</span>
                <span>{settlement.total_settlement_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">已结算</span>
                <span className="text-green-600">{settlement.settled_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">延迟</span>
                <span className="text-red-600">{settlement.delayed_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">平均延迟</span>
                <span>{settlement.avg_delay_days} 天</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">回款总额</span>
                <span>¥{settlement.total_amount?.toLocaleString()}</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400">无回款数据</p>
          )}
        </div>

        {/* 还款计划 */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-700 mb-4">📅 还款计划</h3>
          {plan ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">总金额</span>
                <span>¥{plan.total_amount?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">期数</span>
                <span>{plan.term_months} 个月</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">月还款</span>
                <span>¥{plan.monthly_payment?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">利率</span>
                <span>{((plan.interest_rate || 0) * 100).toFixed(1)}%</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400">无还款计划</p>
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
          {task.approval_status === "DRAFT" && (
            <button
              onClick={() => handleStatusChange("PENDING_REVIEW")}
              disabled={actionLoading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              提交审核
            </button>
          )}
          {task.approval_status === "PENDING_REVIEW" && (
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
