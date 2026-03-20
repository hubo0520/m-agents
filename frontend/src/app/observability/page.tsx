"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getObservabilitySummary,
  getLatencyTrend,
  getAgentLatency,
  getWorkflowStatusDist,
} from "@/lib/api";
import { Card, CardTitle } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

/* ─── 类型定义 ─── */
interface SummaryData {
  today_analysis_count: number;
  today_change_pct: number;
  avg_latency_ms: number;
  llm_success_rate: number;
  total_agent_runs: number;
  degradation_count: number;
}

interface TrendItem {
  date: string;
  avg_latency_ms: number;
  count: number;
}

interface AgentLatencyItem {
  agent_name: string;
  avg_latency_ms: number;
  count: number;
}

interface WorkflowStatusItem {
  status: string;
  count: number;
  percentage: number;
}

/* ─── 常量 ─── */
const TIME_RANGES = [
  { label: "1天", value: 1 },
  { label: "7天", value: 7 },
  { label: "30天", value: 30 },
];

const PIE_COLORS = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
  "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1",
];

const STATUS_LABELS: Record<string, string> = {
  NEW: "新建",
  TRIAGED: "已分诊",
  ANALYZING: "分析中",
  RECOMMENDING: "推荐中",
  PENDING_APPROVAL: "待审批",
  EXECUTING: "执行中",
  COMPLETED: "已完成",
  FAILED_RETRYABLE: "失败可重试",
  FAILED_FINAL: "最终失败",
  PAUSED: "已暂停",
  REJECTED: "已拒绝",
};

/* ─── 指标卡组件 ─── */
function MetricCard({
  title,
  value,
  unit,
  change,
  icon,
}: {
  title: string;
  value: string | number;
  unit?: string;
  change?: number;
  icon: string;
}) {
  return (
    <Card className="flex-1 min-w-0">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-slate-400 mb-1">{title}</p>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-bold text-slate-800">{value}</span>
            {unit && <span className="text-sm text-slate-500">{unit}</span>}
          </div>
          {change !== undefined && (
            <div className={`flex items-center gap-0.5 mt-1 text-xs font-medium ${
              change >= 0 ? "text-green-600" : "text-red-600"
            }`}>
              <span>{change >= 0 ? "↑" : "↓"}</span>
              <span>{Math.abs(change)}%</span>
              <span className="text-slate-400 font-normal ml-0.5">vs 昨日</span>
            </div>
          )}
        </div>
        <span className="text-2xl">{icon}</span>
      </div>
    </Card>
  );
}

/* ─── 主组件 ─── */
export default function ObservabilityPage() {
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [trend, setTrend] = useState<TrendItem[]>([]);
  const [agentLatency, setAgentLatency] = useState<AgentLatencyItem[]>([]);
  const [workflowStatus, setWorkflowStatus] = useState<WorkflowStatusItem[]>([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [summaryRes, trendRes, agentRes, statusRes] = await Promise.all([
        getObservabilitySummary(days),
        getLatencyTrend(days),
        getAgentLatency(days),
        getWorkflowStatusDist(days),
      ]);
      setSummary(summaryRes);
      setTrend(trendRes.trend);
      setAgentLatency(agentRes.agents);
      setWorkflowStatus(statusRes.statuses);
    } catch (err) {
      console.error("加载可观测数据失败:", err);
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading && !summary) {
    return <Spinner label="加载可观测数据..." />;
  }

  return (
    <div className="animate-fade-in">
      {/* 页面标题 + 时间范围选择器 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-800">📊 Agent 可观测面板</h1>
          <p className="text-sm text-slate-400 mt-0.5">监控 Agent 运行状态与性能趋势</p>
        </div>
        <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-0.5">
          {TIME_RANGES.map((range) => (
            <button
              key={range.value}
              onClick={() => setDays(range.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                days === range.value
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      {/* 指标卡 */}
      {summary && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <MetricCard
            title="今日分析量"
            value={summary.today_analysis_count}
            change={summary.today_change_pct}
            icon="📈"
          />
          <MetricCard
            title="平均响应时间"
            value={summary.avg_latency_ms.toFixed(1)}
            unit="ms"
            icon="⏱️"
          />
          <MetricCard
            title="LLM 调用成功率"
            value={summary.llm_success_rate.toFixed(1)}
            unit="%"
            icon="✅"
          />
          <MetricCard
            title="降级触发次数"
            value={summary.degradation_count}
            icon="⚠️"
          />
        </div>
      )}

      {/* 图表区域 */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* 响应时间趋势折线图 */}
        <Card>
          <CardTitle className="mb-4">响应时间趋势</CardTitle>
          {trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10 }}
                  tickFormatter={(v) => v.slice(5)}
                />
                <YAxis tick={{ fontSize: 10 }} unit="ms" />
                <Tooltip
                  formatter={(value: number) => [`${value.toFixed(1)} ms`, "平均耗时"]}
                  labelFormatter={(label) => `日期: ${label}`}
                />
                <Line
                  type="monotone"
                  dataKey="avg_latency_ms"
                  name="平均耗时"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[280px] flex items-center justify-center text-sm text-slate-400">
              暂无数据
            </div>
          )}
        </Card>

        {/* Agent 节点耗时水平条形图 */}
        <Card>
          <CardTitle className="mb-4">Agent 节点耗时排行</CardTitle>
          {agentLatency.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={agentLatency} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tick={{ fontSize: 10 }} unit="ms" />
                <YAxis
                  type="category"
                  dataKey="agent_name"
                  tick={{ fontSize: 10 }}
                  width={120}
                />
                <Tooltip
                  formatter={(value: number) => [`${value.toFixed(1)} ms`, "平均耗时"]}
                />
                <Bar dataKey="avg_latency_ms" name="平均耗时" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[280px] flex items-center justify-center text-sm text-slate-400">
              暂无数据
            </div>
          )}
        </Card>
      </div>

      {/* 工作流状态分布饼图 */}
      <Card>
        <CardTitle className="mb-4">工作流状态分布</CardTitle>
        {workflowStatus.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={workflowStatus}
                dataKey="count"
                nameKey="status"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={({ status, percentage }) =>
                  `${STATUS_LABELS[status] || status} ${percentage}%`
                }
              >
                {workflowStatus.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number, name: string) => [
                  value,
                  STATUS_LABELS[name] || name,
                ]}
              />
              <Legend
                formatter={(value: string) => STATUS_LABELS[value] || value}
              />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-[300px] flex items-center justify-center text-sm text-slate-400">
            暂无数据
          </div>
        )}
      </Card>
    </div>
  );
}
