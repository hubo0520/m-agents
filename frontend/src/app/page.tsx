"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getDashboardStats, getRiskCases, analyzeCase, getApprovals, getWorkflows } from "@/lib/api";
import { getCaseStatusLabel, getCaseStatusColor, getApprovalTypeLabel, getRoleName, getAgentName } from "@/lib/constants";
import { StatCard } from "@/components/ui/StatCard";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { toast } from "sonner";
import type {
  DashboardStats,
  RiskCaseListItem,
  PaginatedResponse,
  ApprovalTask,
  WorkflowRun,
} from "@/types";

/* ────────── 风险等级标签 ────────── */
function RiskBadge({ level }: { level: string }) {
  const variantMap: Record<string, "danger" | "warning" | "success"> = {
    high: "danger",
    medium: "warning",
    low: "success",
  };
  return (
    <Badge variant={variantMap[level] || "muted"} size="sm" dot>
      {level.toUpperCase()}
    </Badge>
  );
}

/* ────────── 状态标签 ────────── */
function StatusBadge({ status }: { status: string }) {
  // 根据状态映射 variant
  const getVariant = (s: string) => {
    if (["APPROVED", "COMPLETED", "REVIEWED"].includes(s)) return "success";
    if (["PENDING_APPROVAL", "PENDING_REVIEW", "NEW"].includes(s)) return "warning";
    if (["REJECTED", "FAILED_RETRYABLE", "FAILED_FINAL", "BLOCKED_BY_GUARD"].includes(s)) return "danger";
    if (["ANALYZING", "RECOMMENDING", "EXECUTING"].includes(s)) return "info";
    return "default";
  };
  return (
    <Badge variant={getVariant(status) as any} size="sm">
      {getCaseStatusLabel(status)}
    </Badge>
  );
}

/* ────────── 风险指挥台主页 ────────── */
export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [data, setData] = useState<PaginatedResponse<RiskCaseListItem> | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzingId, setAnalyzingId] = useState<number | null>(null);

  const [pendingApprovals, setPendingApprovals] = useState<ApprovalTask[]>([]);
  const [failedWorkflows, setFailedWorkflows] = useState<WorkflowRun[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [failedCount, setFailedCount] = useState(0);

  const [riskLevel, setRiskLevel] = useState("");
  const [status, setStatus] = useState("");
  const [merchantName, setMerchantName] = useState("");
  const [sortBy, setSortBy] = useState("");
  const [page, setPage] = useState(1);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, casesRes, approvalsRes, workflowsRes] = await Promise.all([
        getDashboardStats().catch(() => null),
        getRiskCases({
          risk_level: riskLevel || undefined,
          status: status || undefined,
          merchant_name: merchantName || undefined,
          sort_by: sortBy || undefined,
          page,
          page_size: 20,
        }).catch(() => null),
        getApprovals({ status: "PENDING", page_size: 5 }).catch(() => ({ items: [], total: 0 })),
        getWorkflows({ status: "FAILED_RETRYABLE", page_size: 5 }).catch(() => ({ items: [], total: 0 })),
      ]);
      if (statsRes) setStats(statsRes);
      if (casesRes) setData(casesRes);
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
      toast.success("分析完成");
      await fetchData();
    } catch (err) {
      toast.error("分析失败: " + (err as Error).message);
    } finally {
      setAnalyzingId(null);
    }
  };

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="风险指挥台"
        description="实时监控商家经营风险，跟踪高风险案件处理进度"
      />

      {/* ── 顶部指标卡 ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4 mb-8">
        <StatCard
          label="监控商家数"
          value={stats?.merchant_count?.toString() ?? "-"}
          color="text-slate-800"
        />
        <StatCard
          label="今日新增高风险"
          value={stats?.new_high_risk_count?.toString() ?? "0"}
          color="text-red-600"
        />
        <StatCard
          label="预计总现金缺口"
          value={stats ? `¥${stats.total_predicted_gap.toLocaleString()}` : "-"}
          color="text-orange-600"
        />
        <StatCard
          label="平均回款延迟"
          value={stats ? `${stats.avg_settlement_delay}天` : "-"}
          color="text-amber-600"
        />
        <StatCard
          label="待审批"
          value={pendingCount.toString()}
          color="text-amber-600"
          onClick={() => router.push("/approvals?status=PENDING")}
          icon={<span className="text-base">⏳</span>}
        />
        <StatCard
          label="失败工作流"
          value={failedCount.toString()}
          color="text-red-600"
          onClick={() => router.push("/workflows?status=FAILED_RETRYABLE")}
          icon={<span className="text-base">⚠️</span>}
        />
      </div>

      {/* ── 快捷面板 ── */}
      {(pendingApprovals.length > 0 || failedWorkflows.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-8">
          {pendingApprovals.length > 0 && (
            <Card padding="none">
              <CardHeader className="px-5 pt-4 pb-0">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-md bg-amber-50 flex items-center justify-center">
                    <span className="text-xs">⏳</span>
                  </div>
                  <CardTitle>待审批事项</CardTitle>
                </div>
                <a href="/approvals" className="text-xs text-blue-600 hover:text-blue-700 font-medium">
                  查看全部 →
                </a>
              </CardHeader>
              <div className="px-3 pb-3 pt-2">
                {pendingApprovals.slice(0, 3).map((a) => (
                  <div
                    key={a.id}
                    className="flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer hover:bg-slate-50 transition-colors group"
                    onClick={() => router.push(`/approvals/${a.id}`)}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-slate-700 group-hover:text-slate-900">案件 #{a.case_id}</span>
                      <Badge variant="info" size="sm">{getApprovalTypeLabel(a.approval_type)}</Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400">{getRoleName(a.assignee_role ?? "")}</span>
                      <svg className="w-3.5 h-3.5 text-slate-300 group-hover:text-slate-500" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                      </svg>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
          {failedWorkflows.length > 0 && (
            <Card padding="none">
              <CardHeader className="px-5 pt-4 pb-0">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-md bg-red-50 flex items-center justify-center">
                    <span className="text-xs">⚠️</span>
                  </div>
                  <CardTitle>失败工作流</CardTitle>
                </div>
                <a href="/workflows?status=FAILED_RETRYABLE" className="text-xs text-blue-600 hover:text-blue-700 font-medium">
                  查看全部 →
                </a>
              </CardHeader>
              <div className="px-3 pb-3 pt-2">
                {failedWorkflows.slice(0, 3).map((w) => (
                  <div
                    key={w.id}
                    className="flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer hover:bg-slate-50 transition-colors group"
                    onClick={() => router.push(`/workflows/${w.id}`)}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-slate-700 group-hover:text-slate-900">工作流 #{w.id}</span>
                      <span className="text-xs text-slate-400">案件 #{w.case_id}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400">{getAgentName(w.current_node ?? "")}</span>
                      <svg className="w-3.5 h-3.5 text-slate-300 group-hover:text-slate-500" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                      </svg>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ── 筛选区 ── */}
      <Card className="mb-6" padding="none">
        <div className="px-4 sm:px-5 py-3 sm:py-4 flex flex-col sm:flex-row gap-3 sm:gap-5 flex-wrap items-stretch sm:items-end">
          <div>
            <label className="text-xs font-medium text-slate-500 block mb-1.5">风险等级</label>
            <select
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white w-full sm:min-w-[120px] hover:border-slate-300"
              value={riskLevel}
              onChange={(e) => { setRiskLevel(e.target.value); setPage(1); }}
            >
              <option value="">全部</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 block mb-1.5">案件状态</label>
            <select
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white w-full sm:min-w-[120px] hover:border-slate-300"
              value={status}
              onChange={(e) => { setStatus(e.target.value); setPage(1); }}
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
            <label className="text-xs font-medium text-slate-500 block mb-1.5">商家名称</label>
            <input
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white w-full sm:min-w-[160px] hover:border-slate-300 placeholder:text-slate-300"
              placeholder="搜索商家..."
              value={merchantName}
              onChange={(e) => { setMerchantName(e.target.value); setPage(1); }}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 block mb-1.5">排序</label>
            <select
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white w-full sm:min-w-[120px] hover:border-slate-300"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="">更新时间</option>
              <option value="predicted_gap">预测缺口</option>
              <option value="risk_level">风险等级</option>
            </select>
          </div>
        </div>
      </Card>

      {/* ── 案件列表表格 ── */}
      <Card padding="none" className="overflow-hidden">
        {loading ? (
          <Spinner label="加载案件数据..." />
        ) : !data || data.items.length === 0 ? (
          <EmptyState
            title="暂无风险案件"
            description="当前筛选条件下没有匹配的案件"
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100">
                    <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">商家名称</th>
                    <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">行业</th>
                    <th className="text-right px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">7日退货率</th>
                    <th className="text-right px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">基线退货率</th>
                    <th className="text-right px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">放大倍数</th>
                    <th className="text-right px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">预测缺口</th>
                    <th className="text-center px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">风险等级</th>
                    <th className="text-center px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">建议数</th>
                    <th className="text-center px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">状态</th>
                    <th className="text-center px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item) => (
                    <tr
                      key={item.id}
                      className="border-b border-slate-50 table-row-hover cursor-pointer"
                      onClick={() => router.push(`/cases/${item.id}`)}
                    >
                      <td className="px-5 py-3.5 font-medium text-slate-800">{item.merchant_name}</td>
                      <td className="px-5 py-3.5 text-slate-500">{item.industry}</td>
                      <td className="px-5 py-3.5 text-right tabular-nums">
                        {item.return_rate_7d != null ? `${(item.return_rate_7d * 100).toFixed(1)}%` : "-"}
                      </td>
                      <td className="px-5 py-3.5 text-right tabular-nums text-slate-500">
                        {item.baseline_return_rate != null ? `${(item.baseline_return_rate * 100).toFixed(1)}%` : "-"}
                      </td>
                      <td className="px-5 py-3.5 text-right tabular-nums">
                        {item.return_amplification != null ? `${item.return_amplification}x` : "-"}
                      </td>
                      <td className="px-5 py-3.5 text-right tabular-nums font-medium">
                        {item.predicted_gap != null ? `¥${item.predicted_gap.toLocaleString()}` : "-"}
                      </td>
                      <td className="px-5 py-3.5 text-center">
                        <RiskBadge level={item.risk_level} />
                      </td>
                      <td className="px-5 py-3.5 text-center tabular-nums text-slate-600">
                        {item.recommendation_count}
                      </td>
                      <td className="px-5 py-3.5 text-center">
                        <StatusBadge status={item.status} />
                      </td>
                      <td className="px-5 py-3.5 text-center">
                        <button
                          className="text-xs px-3 py-1.5 rounded-md text-blue-600 hover:bg-blue-50 font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                          onClick={(e) => handleAnalyze(item.id, e)}
                          disabled={analyzingId === item.id}
                        >
                          {analyzingId === item.id ? (
                            <span className="flex items-center gap-1.5">
                              <span className="w-3 h-3 rounded-full border border-blue-300 border-t-blue-600 animate-spin" />
                              分析中
                            </span>
                          ) : "重新分析"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* 分页 */}
            {data.total > data.page_size && (
              <div className="flex justify-between items-center px-5 py-3.5 border-t border-slate-100">
                <span className="text-xs text-slate-400">
                  共 {data.total} 条，第 {data.page} / {Math.ceil(data.total / data.page_size)} 页
                </span>
                <div className="flex gap-1.5">
                  <button
                    className="px-3 py-1.5 text-xs font-medium border border-slate-200 rounded-md hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
                    disabled={page <= 1}
                    onClick={() => setPage(page - 1)}
                  >
                    上一页
                  </button>
                  <button
                    className="px-3 py-1.5 text-xs font-medium border border-slate-200 rounded-md hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
                    disabled={page >= Math.ceil(data.total / data.page_size)}
                    onClick={() => setPage(page + 1)}
                  >
                    下一页
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
