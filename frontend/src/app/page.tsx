"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getDashboardStats, getRiskCases, analyzeCase, getApprovals, getWorkflows } from "@/lib/api";
import { getCaseStatusLabel, getCaseStatusColor, getApprovalTypeLabel, getRoleName, getAgentName } from "@/lib/constants";
import type {
  DashboardStats,
  RiskCaseListItem,
  PaginatedResponse,
  ApprovalTask,
  WorkflowRun,
} from "@/types";

/* ────────── 风险等级标签 ────────── */
function RiskBadge({ level }: { level: string }) {
  const styles: Record<string, string> = {
    high: "bg-red-100 text-red-700",
    medium: "bg-amber-100 text-amber-700",
    low: "bg-green-100 text-green-700",
  };
  return (
    <span
      className={`px-2 py-0.5 rounded text-xs font-medium ${styles[level] || "bg-gray-100 text-gray-600"}`}
    >
      {level.toUpperCase()}
    </span>
  );
}

/* ────────── 状态标签 ────────── */
function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`px-2 py-0.5 rounded text-xs font-medium ${getCaseStatusColor(status)}`}
    >
      {getCaseStatusLabel(status)}
    </span>
  );
}

/* ────────── 指标卡 ────────── */
function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
      <p className="text-sm text-slate-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

/* ────────── 风险指挥台主页 ────────── */
export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [data, setData] = useState<PaginatedResponse<RiskCaseListItem> | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [analyzingId, setAnalyzingId] = useState<number | null>(null);

  // V3: 审批 & 工作流统计
  const [pendingApprovals, setPendingApprovals] = useState<ApprovalTask[]>([]);
  const [failedWorkflows, setFailedWorkflows] = useState<WorkflowRun[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [failedCount, setFailedCount] = useState(0);

  // 筛选状态
  const [riskLevel, setRiskLevel] = useState("");
  const [status, setStatus] = useState("");
  const [merchantName, setMerchantName] = useState("");
  const [sortBy, setSortBy] = useState("");
  const [page, setPage] = useState(1);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, casesRes, approvalsRes, workflowsRes] = await Promise.all([
        getDashboardStats(),
        getRiskCases({
          risk_level: riskLevel || undefined,
          status: status || undefined,
          merchant_name: merchantName || undefined,
          sort_by: sortBy || undefined,
          page,
          page_size: 20,
        }),
        getApprovals({ status: "PENDING", page_size: 5 }).catch(() => ({ items: [], total: 0 })),
        getWorkflows({ status: "FAILED_RETRYABLE", page_size: 5 }).catch(() => ({ items: [], total: 0 })),
      ]);
      setStats(statsRes);
      setData(casesRes);
      setPendingApprovals((approvalsRes as any).items || []);
      setPendingCount((approvalsRes as any).total || 0);
      setFailedWorkflows((workflowsRes as any).items || []);
      setFailedCount((workflowsRes as any).total || 0);
    } catch (err) {
      console.error("加载数据失败:", err);
    } finally {
      setLoading(false);
    }
  }, [riskLevel, status, merchantName, sortBy, page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAnalyze = async (caseId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setAnalyzingId(caseId);
    try {
      await analyzeCase(caseId);
      await fetchData();
    } catch (err) {
      alert("分析失败: " + (err as Error).message);
    } finally {
      setAnalyzingId(null);
    }
  };

  return (
    <div>
      {/* 顶部指标卡 */}
      <div className="grid grid-cols-6 gap-4 mb-6">
        <StatCard
          label="监控商家数"
          value={stats?.merchant_count?.toString() ?? "-"}
          color="text-slate-800"
        />
        <StatCard
          label="今日新增高风险案件"
          value={stats?.new_high_risk_count?.toString() ?? "0"}
          color="text-red-600"
        />
        <StatCard
          label="预计总现金缺口"
          value={
            stats ? `¥${stats.total_predicted_gap.toLocaleString()}` : "-"
          }
          color="text-orange-600"
        />
        <StatCard
          label="平均回款延迟"
          value={stats ? `${stats.avg_settlement_delay}天` : "-"}
          color="text-amber-600"
        />
        <div
          className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm cursor-pointer hover:border-yellow-400 transition-colors"
          onClick={() => router.push("/approvals?status=PENDING")}
        >
          <p className="text-sm text-slate-500 mb-1">⏳ 待审批</p>
          <p className="text-2xl font-bold text-yellow-600">{pendingCount}</p>
        </div>
        <div
          className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm cursor-pointer hover:border-red-400 transition-colors"
          onClick={() => router.push("/workflows?status=FAILED_RETRYABLE")}
        >
          <p className="text-sm text-slate-500 mb-1">🔴 失败工作流</p>
          <p className="text-2xl font-bold text-red-600">{failedCount}</p>
        </div>
      </div>

      {/* V3: 快捷面板 */}
      {(pendingApprovals.length > 0 || failedWorkflows.length > 0) && (
        <div className="grid grid-cols-2 gap-4 mb-6">
          {/* 高优先级待审批 */}
          {pendingApprovals.length > 0 && (
            <div className="bg-white rounded-lg border border-yellow-200 p-4 shadow-sm">
              <div className="flex justify-between items-center mb-3">
                <h3 className="font-semibold text-sm text-yellow-800">⏳ 待审批事项</h3>
                <a href="/approvals" className="text-xs text-blue-600 hover:underline">查看全部 →</a>
              </div>
              <div className="space-y-2">
                {pendingApprovals.slice(0, 3).map((a) => (
                  <div key={a.id} className="flex justify-between items-center text-sm cursor-pointer hover:bg-yellow-50 rounded p-1"
                    onClick={() => router.push(`/approvals/${a.id}`)}>
                    <span>案件 #{a.case_id} · {getApprovalTypeLabel(a.approval_type)}</span>
                    <span className="text-xs text-gray-400">{getRoleName(a.assignee_role ?? "")}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {/* 失败工作流 */}
          {failedWorkflows.length > 0 && (
            <div className="bg-white rounded-lg border border-red-200 p-4 shadow-sm">
              <div className="flex justify-between items-center mb-3">
                <h3 className="font-semibold text-sm text-red-800">🔴 失败工作流</h3>
                <a href="/workflows?status=FAILED_RETRYABLE" className="text-xs text-blue-600 hover:underline">查看全部 →</a>
              </div>
              <div className="space-y-2">
                {failedWorkflows.slice(0, 3).map((w) => (
                  <div key={w.id} className="flex justify-between items-center text-sm cursor-pointer hover:bg-red-50 rounded p-1"
                    onClick={() => router.push(`/workflows/${w.id}`)}>
                    <span>工作流 #{w.id} · 案件 #{w.case_id}</span>
                    <span className="text-xs text-gray-400">{getAgentName(w.current_node ?? "")}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 筛选区 */}
      <div className="bg-white rounded-lg border border-slate-200 p-4 mb-6 flex gap-4 flex-wrap items-end">
        <div>
          <label className="text-xs text-slate-500 block mb-1">风险等级</label>
          <select
            className="border border-slate-300 rounded px-3 py-1.5 text-sm"
            value={riskLevel}
            onChange={(e) => {
              setRiskLevel(e.target.value);
              setPage(1);
            }}
          >
            <option value="">全部</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-slate-500 block mb-1">案件状态</label>
          <select
            className="border border-slate-300 rounded px-3 py-1.5 text-sm"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">全部</option>
            <option value="NEW">新建</option>
            <option value="ANALYZED">已分析</option>
            <option value="PENDING_REVIEW">待审核</option>
            <option value="APPROVED">已通过</option>
            <option value="REJECTED">已驳回</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-slate-500 block mb-1">商家名称</label>
          <input
            className="border border-slate-300 rounded px-3 py-1.5 text-sm"
            placeholder="搜索商家"
            value={merchantName}
            onChange={(e) => {
              setMerchantName(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <div>
          <label className="text-xs text-slate-500 block mb-1">排序</label>
          <select
            className="border border-slate-300 rounded px-3 py-1.5 text-sm"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <option value="">更新时间</option>
            <option value="predicted_gap">预测缺口</option>
            <option value="risk_level">风险等级</option>
          </select>
        </div>
      </div>

      {/* 案件列表表格 */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-x-auto">
        {loading ? (
          <div className="p-8 text-center text-slate-400">加载中...</div>
        ) : !data || data.items.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            暂无风险案件
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-4 py-3 text-slate-600 font-medium">
                  商家名称
                </th>
                <th className="text-left px-4 py-3 text-slate-600 font-medium">
                  行业
                </th>
                <th className="text-right px-4 py-3 text-slate-600 font-medium">
                  7日退货率
                </th>
                <th className="text-right px-4 py-3 text-slate-600 font-medium">
                  基线退货率
                </th>
                <th className="text-right px-4 py-3 text-slate-600 font-medium">
                  放大倍数
                </th>
                <th className="text-right px-4 py-3 text-slate-600 font-medium">
                  预测缺口
                </th>
                <th className="text-center px-4 py-3 text-slate-600 font-medium">
                  风险等级
                </th>
                <th className="text-center px-4 py-3 text-slate-600 font-medium">
                  建议数
                </th>
                <th className="text-center px-4 py-3 text-slate-600 font-medium">
                  状态
                </th>
                <th className="text-center px-4 py-3 text-slate-600 font-medium">
                  操作
                </th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr
                  key={item.id}
                  className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
                  onClick={() => router.push(`/cases/${item.id}`)}
                >
                  <td className="px-4 py-3 font-medium">{item.merchant_name}</td>
                  <td className="px-4 py-3 text-slate-500">{item.industry}</td>
                  <td className="px-4 py-3 text-right">
                    {item.return_rate_7d != null
                      ? `${(item.return_rate_7d * 100).toFixed(1)}%`
                      : "-"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {item.baseline_return_rate != null
                      ? `${(item.baseline_return_rate * 100).toFixed(1)}%`
                      : "-"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {item.return_amplification != null
                      ? `${item.return_amplification}x`
                      : "-"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {item.predicted_gap != null
                      ? `¥${item.predicted_gap.toLocaleString()}`
                      : "-"}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <RiskBadge level={item.risk_level} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    {item.recommendation_count}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <StatusBadge status={item.status} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      className="text-xs px-2 py-1 bg-blue-50 text-blue-600 rounded hover:bg-blue-100 transition-colors disabled:opacity-50"
                      onClick={(e) => handleAnalyze(item.id, e)}
                      disabled={analyzingId === item.id}
                    >
                      {analyzingId === item.id ? "分析中..." : "重新分析"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* 分页 */}
        {data && data.total > data.page_size && (
          <div className="flex justify-between items-center px-4 py-3 border-t border-slate-200">
            <span className="text-sm text-slate-500">
              共 {data.total} 条，第 {data.page} / {Math.ceil(data.total / data.page_size)} 页
            </span>
            <div className="flex gap-2">
              <button
                className="px-3 py-1 text-sm border rounded disabled:opacity-50"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                上一页
              </button>
              <button
                className="px-3 py-1 text-sm border rounded disabled:opacity-50"
                disabled={page >= Math.ceil(data.total / data.page_size)}
                onClick={() => setPage(page + 1)}
              >
                下一页
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
