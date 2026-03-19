"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getCaseDetail,
  analyzeCase,
  reviewCase,
  exportCase,
  getCaseTasks,
} from "@/lib/api";
import type { CaseDetail, ReviewRequest, UnifiedTask } from "@/types";
import { getCaseStatusLabel, getCaseStatusColor, getTaskStatusLabel, getTaskStatusColor, getAuditActionLabel, parseAuditValue, getEvidenceTypeLabel, formatEvidenceSummary } from "@/lib/constants";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Card, CardTitle } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  ReferenceLine,
} from "recharts";

/* ────────── 辅助组件 ────────── */
function RiskBadge({ level }: { level: string }) {
  const variantMap: Record<string, "danger" | "warning" | "success"> = {
    high: "danger",
    medium: "warning",
    low: "success",
  };
  return (
    <Badge variant={variantMap[level] || "muted"} size="md" dot>
      {level.toUpperCase()}
    </Badge>
  );
}

function StatusBadge({ status }: { status: string }) {
  const getVariant = (s: string) => {
    if (["APPROVED", "COMPLETED", "REVIEWED"].includes(s)) return "success";
    if (["PENDING_APPROVAL", "PENDING_REVIEW", "NEW"].includes(s)) return "warning";
    if (["REJECTED", "FAILED_RETRYABLE", "FAILED_FINAL"].includes(s)) return "danger";
    if (["ANALYZING", "RECOMMENDING", "EXECUTING"].includes(s)) return "info";
    return "default";
  };
  return (
    <Badge variant={getVariant(status) as any} size="sm">
      {getCaseStatusLabel(status)}
    </Badge>
  );
}

/* ────────── 审批抽屉 ────────── */
function ReviewDrawer({
  open,
  onClose,
  caseData,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  caseData: CaseDetail;
  onSubmit: (req: ReviewRequest) => Promise<void>;
}) {
  const [decision, setDecision] = useState("approve");
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const hasFinanceAction = caseData.recommendations.some(
    (r) => r.action_type === "business_loan" || r.action_type === "anomaly_review"
  );

  const handleSubmit = async () => {
    if (decision === "reject" && !comment.trim()) {
      alert("驳回必须填写理由");
      return;
    }
    if (hasFinanceAction && decision !== "reject" && !comment.trim()) {
      alert("融资类/反欺诈类动作必须填写备注");
      return;
    }
    setSubmitting(true);
    try {
      await onSubmit({ decision, comment, reviewer_id: "operator" });
      onClose();
    } catch (err) {
      alert("审批失败: " + (err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/20 animate-fade-in-overlay" onClick={onClose} />
      <div className="w-[480px] bg-white shadow-xl overflow-y-auto p-6 animate-slide-in-right">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-lg font-bold">审批案件</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl">&times;</button>
        </div>

        {/* Agent 原始建议 */}
        <div className="mb-6">
          <h3 className="text-sm font-medium text-slate-600 mb-2">Agent 建议</h3>
          {caseData.recommendations.map((rec, i) => (
            <div key={i} className="border border-slate-200 rounded p-3 mb-2">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-medium text-sm">{rec.title}</span>
                {rec.requires_manual_review && (
                  <span className="text-xs bg-red-50 text-red-600 px-1.5 py-0.5 rounded">需复核</span>
                )}
              </div>
              <p className="text-xs text-slate-500">{rec.why}</p>
            </div>
          ))}
        </div>

        {/* 审批选项 */}
        <div className="mb-4">
          <h3 className="text-sm font-medium text-slate-600 mb-2">审批决定</h3>
          <div className="flex gap-2">
            {[
              { value: "approve", label: "批准", color: "bg-green-50 border-green-300 text-green-700" },
              { value: "approve_with_changes", label: "修改后批准", color: "bg-blue-50 border-blue-300 text-blue-700" },
              { value: "reject", label: "驳回", color: "bg-red-50 border-red-300 text-red-700" },
            ].map((opt) => (
              <button
                key={opt.value}
                className={`px-3 py-1.5 rounded border text-sm font-medium transition-colors ${
                  decision === opt.value ? opt.color : "bg-white border-slate-200 text-slate-600"
                }`}
                onClick={() => setDecision(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* 备注 */}
        <div className="mb-6">
          <h3 className="text-sm font-medium text-slate-600 mb-2">
            审批意见{(decision === "reject" || hasFinanceAction) && <span className="text-red-500">*</span>}
          </h3>
          <textarea
            className="w-full border border-slate-300 rounded p-3 text-sm"
            rows={4}
            placeholder="请输入审批意见..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
        </div>

        <button
          className="w-full bg-blue-600 text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
          onClick={handleSubmit}
          disabled={submitting}
        >
          {submitting ? "提交中..." : "提交审批"}
        </button>
      </div>
    </div>
  );
}

/* ────────── 案件详情页主组件 ────────── */
export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const caseId = Number(params.id);

  const [data, setData] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const [highlightedEvidence, setHighlightedEvidence] = useState<string | null>(null);

  // 根据 EV-xxx 标签滚动到对应的证据卡片并高亮
  const scrollToEvidence = (eid: string) => {
    // EV-101 对应证据列表索引 0, EV-102 对应索引 1...
    const match = eid.match(/EV-(\d+)/);
    if (match && data) {
      const evIndex = parseInt(match[1], 10) - 101;
      if (evIndex >= 0 && evIndex < data.evidence.length) {
        const targetId = `ev-card-${evIndex}`;
        const el = document.getElementById(targetId);
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
          setHighlightedEvidence(targetId);
          setTimeout(() => setHighlightedEvidence(null), 2000);
        }
      }
    }
  };
  const [caseTasks, setCaseTasks] = useState<UnifiedTask[]>([]);
  const [showTasksTab, setShowTasksTab] = useState(false);

  const fetchDetail = async () => {
    try {
      const detail = await getCaseDetail(caseId);
      setData(detail);
      // V2: 获取关联的执行任务
      try {
        const tasks = await getCaseTasks(caseId);
        setCaseTasks(tasks);
      } catch {
        setCaseTasks([]);
      }
    } catch (err) {
      console.error("加载详情失败:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [caseId]);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      await analyzeCase(caseId);
      await fetchDetail();
    } catch (err) {
      alert("分析失败: " + (err as Error).message);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleReview = async (req: ReviewRequest) => {
    await reviewCase(caseId, req);
    await fetchDetail();
  };

  const handleExport = async (format: "markdown" | "json") => {
    try {
      const content = await exportCase(caseId, format);
      const blob = new Blob(
        [typeof content === "string" ? content : JSON.stringify(content, null, 2)],
        { type: format === "markdown" ? "text/markdown" : "application/json" }
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `RC-${caseId.toString().padStart(4, "0")}.${format === "markdown" ? "md" : "json"}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert("导出失败: " + (err as Error).message);
    }
  };

  if (loading) return <Spinner label="加载案件详情..." />;
  if (!data) return (
    <div className="flex flex-col items-center justify-center py-20">
      <p className="text-sm text-red-500">案件不存在</p>
    </div>
  );

  const agentOutput = data.agent_output;
  const forecast = data.forecast;

  return (
    <div className="animate-fade-in">
      {/* 面包屑导航 + 操作按钮 */}
      <div className="flex justify-between items-center mb-8">
        <div className="flex items-center gap-3">
          <button
            className="text-sm text-slate-500 hover:text-blue-600 transition-colors"
            onClick={() => router.push("/")}
          >
            ← 风险指挥台
          </button>
          <span className="text-slate-200">/</span>
          <span className="text-sm font-medium text-slate-800">案件 RC-{caseId.toString().padStart(4, "0")}</span>
          <RiskBadge level={data.risk_level} />
          <StatusBadge status={data.status} />
        </div>
        <div className="flex gap-2">
          <button
            className="px-3.5 py-1.5 text-xs font-medium border border-slate-200 rounded-lg hover:bg-slate-50 hover:border-slate-300 transition-all disabled:opacity-40"
            onClick={handleAnalyze}
            disabled={analyzing}
          >
            {analyzing ? (
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full border border-slate-300 border-t-blue-600 animate-spin" />
                分析中
              </span>
            ) : "🔄 重新分析"}
          </button>
          {data.status === "ANALYZED" && (
            <button
              className="px-3.5 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              onClick={() => setShowReview(true)}
            >
              📋 审批
            </button>
          )}
          <button
            className="px-3.5 py-1.5 text-xs font-medium border border-slate-200 rounded-lg hover:bg-slate-50 hover:border-slate-300 transition-all"
            onClick={() => handleExport("markdown")}
          >
            📥 MD
          </button>
          <button
            className="px-3.5 py-1.5 text-xs font-medium border border-slate-200 rounded-lg hover:bg-slate-50 hover:border-slate-300 transition-all"
            onClick={() => handleExport("json")}
          >
            📥 JSON
          </button>
        </div>
      </div>

      {/* 左右分栏 */}
      <div className="grid grid-cols-5 gap-6 mb-8">
        {/* 左侧 — 60% */}
        <div className="col-span-3 space-y-5">
          {/* 商家基本信息 */}
          <Card>
            <CardTitle className="mb-4">商家信息</CardTitle>
            <div className="grid grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-slate-400">名称</span>
                <p className="font-medium">{data.merchant.name}</p>
              </div>
              <div>
                <span className="text-slate-400">行业</span>
                <p className="font-medium">{data.merchant.industry}</p>
              </div>
              <div>
                <span className="text-slate-400">店铺等级</span>
                <p className="font-medium">{data.merchant.store_level}</p>
              </div>
              <div>
                <span className="text-slate-400">结算周期</span>
                <p className="font-medium">{data.merchant.settlement_cycle_days}天</p>
              </div>
            </div>
          </Card>

          {/* 风险评分拆解 */}
          {data.metrics && (
            <Card>
              <CardTitle className="mb-4">风险评分拆解</CardTitle>
              <div className="grid grid-cols-4 gap-3 text-sm">
                <div className="text-center p-3 bg-slate-50/80 rounded-lg">
                  <p className="text-xs text-slate-400 mb-1">退货率放大</p>
                  <p className="text-xl font-bold text-orange-600">
                    {data.metrics.return_amplification ?? "-"}x
                  </p>
                </div>
                <div className="text-center p-3 bg-slate-50/80 rounded-lg">
                  <p className="text-xs text-slate-400 mb-1">回款延迟</p>
                  <p className="text-xl font-bold text-amber-600">
                    {data.metrics.avg_settlement_delay ?? "-"}天
                  </p>
                </div>
                <div className="text-center p-3 bg-slate-50/80 rounded-lg">
                  <p className="text-xs text-slate-400 mb-1">7日退款压力</p>
                  <p className="text-xl font-bold text-red-600">
                    ¥{(data.metrics.refund_pressure_7d ?? 0).toLocaleString()}
                  </p>
                </div>
                <div className="text-center p-3 bg-slate-50/80 rounded-lg">
                  <p className="text-xs text-slate-400 mb-1">异常分数</p>
                  <p className="text-xl font-bold text-purple-600">
                    {(data.metrics.anomaly_score ?? 0).toFixed(2)}
                  </p>
                </div>
              </div>
            </Card>
          )}

          {/* 30天趋势图 */}
          {data.trend_data && data.trend_data.length > 0 && (
            <Card>
              <CardTitle className="mb-4">近30天趋势</CardTitle>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={data.trend_data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="order_amount"
                    name="订单金额"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="refund_amount"
                    name="退款金额"
                    stroke="#ef4444"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="settlement_amount"
                    name="回款金额"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          )}

          {/* 14日现金流预测图 */}
          {forecast && forecast.daily_forecast && (
            <Card>
              <CardTitle>14日现金流预测</CardTitle>
              <p className="text-xs text-slate-400 mb-3">
                预测缺口: ¥{forecast.predicted_gap?.toLocaleString() ?? 0} |
                最低现金日: {forecast.lowest_cash_day ?? "-"} |
                置信度: {((forecast.confidence ?? 0) * 100).toFixed(0)}%
              </p>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={forecast.daily_forecast}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="inflow" name="收入" fill="#10b981" />
                  <Bar dataKey="outflow" name="支出" fill="#ef4444" />
                  <ReferenceLine y={0} stroke="#6b7280" />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          )}
        </div>

        {/* 右侧 — 40% */}
        <div className="col-span-2 space-y-5">
          {/* Agent 案件总结 */}
          {data.status === "NEW" ? (
            <Card className="text-center">
              <div className="py-4">
                <p className="text-slate-400 mb-4 text-sm">待分析</p>
                <button
                  className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-40"
                  onClick={handleAnalyze}
                  disabled={analyzing}
                >
                  {analyzing ? "分析中..." : "开始分析"}
                </button>
              </div>
            </Card>
          ) : agentOutput ? (
            <Card>
              <div className="flex items-center gap-2 mb-3">
                <CardTitle>Agent 案件总结</CardTitle>
                <RiskBadge level={agentOutput.risk_level} />
                {agentOutput.manual_review_required && (
                  <span className="text-xs bg-red-50 text-red-600 px-2 py-0.5 rounded">需人工复核</span>
                )}
              </div>
              <p className="text-sm text-slate-700 mb-4">{agentOutput.case_summary}</p>

              {/* 根因列表 */}
              {agentOutput.root_causes.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-xs font-medium text-slate-500 mb-2">核心成因</h4>
                  {agentOutput.root_causes.map((rc, i) => (
                    <div key={i} className="border-l-2 border-orange-300 pl-3 mb-2">
                      <p className="text-sm font-medium">{rc.label}</p>
                      <p className="text-xs text-slate-500">{rc.explanation}</p>
                      <div className="flex gap-1 mt-1">
                        <span className="text-xs text-slate-400">
                          置信度: {(rc.confidence * 100).toFixed(0)}%
                        </span>
                        {rc.evidence_ids.map((eid) => (
                          <button
                            key={eid}
                            className="text-xs text-blue-500 hover:underline cursor-pointer"
                            onClick={() => scrollToEvidence(eid)}
                          >
                            {eid}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                  ))}n                </div>
              )}
            </Card>
          ) : null}

          {/* 动作建议列表 */}
          {data.recommendations.length > 0 && (
            <Card>
              <CardTitle className="mb-3">动作建议</CardTitle>
              {data.recommendations.map((rec, i) => (
                <div
                  key={i}
                  className="border border-slate-200 rounded-lg p-3 mb-2"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium">{rec.title}</span>
                    {rec.requires_manual_review && (
                      <span className="text-xs bg-red-50 text-red-600 px-1.5 py-0.5 rounded">
                        需复核
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mb-1">{rec.why}</p>
                  <div className="flex justify-between text-xs text-slate-400">
                    <span>预期: {
                      typeof rec.expected_benefit === 'string'
                        ? rec.expected_benefit
                        : rec.expected_benefit?.description
                          ? `${rec.expected_benefit.description}${rec.expected_benefit.cash_relief ? `（¥${rec.expected_benefit.cash_relief.toLocaleString()}）` : ''}`
                          : '暂无'
                    }</span>
                    <span>置信度: {(rec.confidence * 100).toFixed(0)}%</span>
                  </div>
                  {rec.evidence_ids && (
                    <div className="flex gap-1 mt-1">
                      {rec.evidence_ids.map((eid) => (
                        <button
                          key={eid}
                          className="text-xs text-blue-500 hover:underline cursor-pointer"
                          onClick={() => scrollToEvidence(eid)}
                        >
                          {eid}
                        </button>
                      ))}
                  </div>
                  )}
                </div>
              ))}
            </Card>
          )}
        </div>
      </div>

      {/* V2: 已自动生成执行任务提示条 */}
      {caseTasks.length > 0 && data.status === "APPROVED" && (
        <Card className="!bg-blue-50 !border-blue-200/60 mb-6" padding="none">
        <div className="px-5 py-3.5 flex items-center justify-between">
          <span className="text-sm text-blue-700">
            ✅ 已自动生成 {caseTasks.length} 条执行任务
          </span>
          <button
            className="text-sm text-blue-600 hover:underline"
            onClick={() => setShowTasksTab(true)}
          >
            查看任务 →
          </button>
        </div>
        </Card>
      )}

      {/* V2: 执行任务 Tab */}
      {showTasksTab && caseTasks.length > 0 && (
        <Card className="mb-6" padding="none">
          <div className="flex items-center justify-between px-5 py-4">
            <CardTitle>执行任务</CardTitle>
            <button
              className="text-xs text-slate-400 hover:text-slate-600"
              onClick={() => setShowTasksTab(false)}
            >
              收起
            </button>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">类型</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">状态</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">金额</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">负责人</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">创建时间</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">操作</th>
              </tr>
            </thead>
            <tbody>
              {caseTasks.map((task) => {
                const typeLabels: Record<string, string> = {
                  financing: "💰 融资申请",
                  claim: "🛡️ 理赔申请",
                  manual_review: "👁️ 人工复核",
                };
                const detailPath =
                  task.task_type === "financing" ? `/tasks/financing/${task.task_id}` :
                  task.task_type === "claim" ? `/tasks/claims/${task.task_id}` :
                  `/tasks/reviews/${task.task_id}`;
                return (
                  <tr key={`${task.task_type}-${task.task_id}`} className="border-b border-slate-50 table-row-hover">
                    <td className="px-5 py-3.5">{typeLabels[task.task_type] || task.task_type}</td>
                    <td className="px-5 py-3.5">
                      <Badge variant={task.status === "COMPLETED" || task.status === "APPROVED" ? "success" : task.status === "REJECTED" ? "danger" : "warning"} size="sm">
                        {getTaskStatusLabel(task.status)}
                      </Badge>
                    </td>
                    <td className="px-5 py-3.5 tabular-nums">{task.amount !== null ? `¥${task.amount.toLocaleString()}` : "-"}</td>
                    <td className="px-5 py-3.5 text-slate-600 text-xs">{task.assigned_to || "-"}</td>
                    <td className="px-5 py-3.5 text-slate-400 text-xs">
                      {task.created_at ? new Date(task.created_at).toLocaleDateString("zh-CN") : "-"}
                    </td>
                    <td className="px-5 py-3.5">
                      <Link href={detailPath} className="text-xs px-3 py-1.5 rounded-md text-blue-600 hover:bg-blue-50 font-medium transition-colors">查看</Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      )}

      {/* 执行任务 Tab 切换按钮（当有任务但未展开时） */}
      {caseTasks.length > 0 && !showTasksTab && (
        <div className="mb-6">
          <button
            className="text-sm text-blue-600 hover:underline"
            onClick={() => setShowTasksTab(true)}
          >
            📋 查看执行任务 ({caseTasks.length})
          </button>
        </div>
      )}

      {/* 底部区域 */}
      <div className="space-y-6">
        {/* 证据链时间线 */}
        {data.evidence.length > 0 && (
          <Card>
            <CardTitle className="mb-4">证据链</CardTitle>
            <div className="space-y-2">
              {data.evidence.map((ev, idx) => {
                const evLabel = `EV-${101 + idx}`;
                const cardId = `ev-card-${idx}`;
                const isHighlighted = highlightedEvidence === cardId;
                return (
                  <div
                    key={ev.id}
                    id={cardId}
                    className={`flex items-start gap-3 p-2 rounded transition-colors duration-500 ${
                      isHighlighted
                        ? "bg-blue-50 ring-2 ring-blue-300"
                        : "hover:bg-slate-50"
                    }`}
                  >
                    <div className="w-2 h-2 rounded-full bg-blue-400 mt-1.5 flex-shrink-0" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs bg-blue-100 text-blue-600 px-1.5 rounded font-mono">
                          {evLabel}
                        </span>
                        <span className="text-xs bg-slate-100 text-slate-600 px-1.5 rounded">
                          {getEvidenceTypeLabel(ev.evidence_type)}
                        </span>
                        {ev.importance_score && (
                          <span className="text-xs text-slate-400">
                            重要度: {ev.importance_score}
                          </span>
                        )}
                      </div>
<p className="text-sm text-slate-700 mt-0.5">{formatEvidenceSummary(ev.summary ?? "")}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        )}

        {/* 审计记录 */}
        {data.audit_logs.length > 0 && (
          <Card>
            <CardTitle className="mb-4">审计记录</CardTitle>
            <div className="space-y-3">
              {data.audit_logs.map((log) => {
                const oldParts = parseAuditValue(log.old_value);
                const newParts = parseAuditValue(log.new_value);
                return (
                  <div key={log.id} className="flex items-start gap-3 border-b border-slate-100 pb-3 last:border-b-0 last:pb-0">
                    {/* 时间线圆点 */}
                    <div className="w-2 h-2 rounded-full bg-blue-400 mt-1.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      {/* 第一行: 操作 + 时间 */}
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-slate-800">
                          {getAuditActionLabel(log.action)}
                        </span>
                        <span className="text-xs text-slate-400">
                          {log.actor === "system" ? "系统" : log.actor}
                        </span>
                        <span className="text-xs text-slate-400 ml-auto flex-shrink-0">
                          {log.created_at ? new Date(log.created_at).toLocaleString("zh-CN") : ""}
                        </span>
                      </div>
                      {/* 第二行: 变更详情 */}
                      <div className="flex items-start gap-2 text-xs">
                        {oldParts.length > 0 && (
                          <div className="flex flex-wrap gap-1 items-center">
                            {oldParts.map((p, i) => (
                              <span key={i} className="inline-flex items-center gap-0.5 bg-red-50 text-red-600 px-1.5 py-0.5 rounded">
                                {p.label ? <span className="text-red-400">{p.label}:</span> : null}
                                <span>{p.value}</span>
                              </span>
                            ))}
                          </div>
                        )}
                        {oldParts.length > 0 && newParts.length > 0 && (
                          <span className="text-slate-400 mt-0.5">→</span>
                        )}
                        {newParts.length > 0 && (
                          <div className="flex flex-wrap gap-1 items-center">
                            {newParts.map((p, i) => (
                              <span key={i} className="inline-flex items-center gap-0.5 bg-green-50 text-green-700 px-1.5 py-0.5 rounded">
                                {p.label ? <span className="text-green-500">{p.label}:</span> : null}
                                <span>{p.value}</span>
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        )}
      </div>

      {/* 审批抽屉 */}
      {data && (
        <ReviewDrawer
          open={showReview}
          onClose={() => setShowReview(false)}
          caseData={data}
          onSubmit={handleReview}
        />
      )}
    </div>
  );
}
