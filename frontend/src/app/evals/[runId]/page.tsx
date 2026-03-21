"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getEvalRun } from "@/lib/api";
import type { EvalRunDetail, EvalResultItem } from "@/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import MarkdownRenderer from "@/components/MarkdownRenderer";

// 评分配色
function scoreColor(score: number | null): string {
  if (score == null) return "text-slate-400";
  if (score >= 80) return "text-emerald-600";
  if (score >= 60) return "text-amber-600";
  return "text-red-600";
}

function scoreBg(score: number | null): string {
  if (score == null) return "bg-slate-50";
  if (score >= 80) return "bg-emerald-50";
  if (score >= 60) return "bg-amber-50";
  return "bg-red-50";
}

// 安全解析 JSON
function safeParseJSON(str: string | null): Record<string, unknown> | null {
  if (!str) return null;
  try {
    return JSON.parse(str);
  } catch {
    return null;
  }
}

export default function EvalRunDetailPage() {
  const params = useParams();
  const router = useRouter();
  const runId = Number(params.runId);
  const [detail, setDetail] = useState<EvalRunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!runId) return;
    const fetchDetail = async () => {
      const data = await getEvalRun(runId);
      setDetail(data);
      setLoading(false);

      // 如果还在运行中，启动轮询
      if (data.status === "RUNNING" && !pollRef.current) {
        pollRef.current = setInterval(async () => {
          const updated = await getEvalRun(runId);
          setDetail(updated);
          if (updated.status !== "RUNNING") {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
          }
        }, 3000);
      }
    };
    fetchDetail();

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [runId]);

  if (loading || !detail) return <Spinner label="加载评测详情..." />;

  // 计算汇总指标
  const results = detail.results || [];
  const judgeScores = results.filter((r) => r.judge_score != null).map((r) => r.judge_score!);
  const avgJudge = judgeScores.length > 0 ? judgeScores.reduce((a, b) => a + b, 0) / judgeScores.length : null;
  const riskMatchRate = results.length > 0 ? results.filter((r) => r.risk_level_match === 1).length / results.length : null;
  const rootCauseRate = results.length > 0 ? results.filter((r) => r.root_cause_match === 1).length / results.length : null;
  const halluRate = results.length > 0 ? results.filter((r) => r.has_hallucination === 1).length / results.length : null;
  const latencies = results.filter((r) => r.latency_ms != null && r.latency_ms > 0).map((r) => r.latency_ms!);
  const avgLatency = latencies.length > 0 ? latencies.reduce((a, b) => a + b, 0) / latencies.length : null;

  const metricCards = [
    { label: "Judge 平均评分", value: avgJudge != null ? avgJudge.toFixed(1) : "-", color: scoreColor(avgJudge) },
    { label: "风险等级匹配率", value: riskMatchRate != null ? `${(riskMatchRate * 100).toFixed(0)}%` : "-", color: riskMatchRate != null && riskMatchRate >= 0.8 ? "text-emerald-600" : "text-amber-600" },
    { label: "根因覆盖率", value: rootCauseRate != null ? `${(rootCauseRate * 100).toFixed(0)}%` : "-", color: rootCauseRate != null && rootCauseRate >= 0.8 ? "text-emerald-600" : "text-amber-600" },
    { label: "幻觉率", value: halluRate != null ? `${(halluRate * 100).toFixed(0)}%` : "-", color: halluRate != null && halluRate <= 0.1 ? "text-emerald-600" : "text-red-600" },
    { label: "Schema 合格率", value: detail.schema_pass_rate != null ? `${(detail.schema_pass_rate * 100).toFixed(0)}%` : "-", color: "text-slate-700" },
    { label: "平均延迟", value: avgLatency != null ? `${(avgLatency / 1000).toFixed(1)}s` : "-", color: "text-slate-700" },
  ];

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <Link href="/evals" className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1 mb-3">
          ← 返回评测中心
        </Link>
        <PageHeader
          title={`评测运行 #${detail.id}`}
          description={`数据集 #${detail.dataset_id} · 模型 ${detail.model_name} · ${detail.status === "RUNNING" ? `运行中 ${detail.completed_count}/${detail.total_count}` : detail.status === "COMPLETED" ? "已完成" : detail.status}`}
        />
      </div>

      {/* 进度条（运行中） */}
      {detail.status === "RUNNING" && (
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="flex-1 h-3 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all duration-500"
                style={{ width: `${detail.total_count > 0 ? (detail.completed_count / detail.total_count) * 100 : 0}%` }}
              />
            </div>
            <span className="text-sm font-medium text-blue-600">
              {detail.completed_count}/{detail.total_count}
            </span>
          </div>
        </div>
      )}

      {/* 汇总指标卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
        {metricCards.map((m) => (
          <Card key={m.label} className="text-center">
            <div className={`text-2xl font-bold tabular-nums ${m.color}`}>{m.value}</div>
            <div className="text-xs text-slate-500 mt-1">{m.label}</div>
          </Card>
        ))}
      </div>

      {/* 逐条用例结果 */}
      <h2 className="text-base font-semibold text-slate-800 mb-4">测试用例结果</h2>
      <div className="space-y-3">
        {results.map((r, idx) => {
          const expected = safeParseJSON(r.expected_output_json);
          const actual = safeParseJSON(r.actual_output_json);
          const isExpanded = expandedIndex === idx;
          const hasError = !!actual?.error;

          return (
            <Card key={idx} padding="none" className="overflow-hidden">
              {/* 用例摘要行 */}
              <div
                className="flex items-center px-5 py-3.5 cursor-pointer hover:bg-slate-50 transition-colors"
                onClick={() => setExpandedIndex(isExpanded ? null : idx)}
              >
                <div className="flex-1 flex items-center gap-3">
                  <span className="font-mono text-xs text-slate-400">#{r.test_case_index + 1}</span>
                  <span className="text-sm text-slate-700">
                    case_id: {safeParseJSON(r.input_json)?.case_id as string || "N/A"}
                  </span>
                  {hasError && <Badge variant="danger" size="sm">错误</Badge>}
                </div>
                <div className="flex items-center gap-4">
                  {/* Judge 评分 */}
                  <div className={`text-sm font-bold tabular-nums ${scoreColor(r.judge_score)}`}>
                    {r.judge_score != null ? r.judge_score : "-"}
                  </div>
                  {/* 指标标签 */}
                  <div className="flex gap-1">
                    {r.risk_level_match === 1 && <Badge variant="success" size="sm">等级✓</Badge>}
                    {r.risk_level_match === 0 && <Badge variant="danger" size="sm">等级✗</Badge>}
                    {r.root_cause_match === 1 && <Badge variant="success" size="sm">根因✓</Badge>}
                    {r.root_cause_match === 0 && <Badge variant="danger" size="sm">根因✗</Badge>}
                    {r.has_hallucination === 1 && <Badge variant="danger" size="sm">幻觉</Badge>}
                  </div>
                  {/* 延迟 */}
                  <span className="text-xs text-slate-400 tabular-nums w-16 text-right">
                    {r.latency_ms != null ? `${(r.latency_ms / 1000).toFixed(1)}s` : "-"}
                  </span>
                  <span className="text-slate-300">{isExpanded ? "▲" : "▼"}</span>
                </div>
              </div>

              {/* 展开详情 */}
              {isExpanded && (
                <div className="border-t border-slate-100 px-5 py-4 space-y-4">
                  {/* Judge 评分理由 */}
                  {r.judge_reasoning && (
                    <div className={`rounded-lg p-4 ${scoreBg(r.judge_score)}`}>
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs font-semibold text-slate-600">🤖 LLM-Judge 评分理由</span>
                        <span className={`text-lg font-bold ${scoreColor(r.judge_score)}`}>
                          {r.judge_score}/100
                        </span>
                      </div>
                      <div className="text-sm text-slate-700">
                        <MarkdownRenderer content={r.judge_reasoning} />
                      </div>
                    </div>
                  )}

                  {/* Judge 输入/输出详情 */}
                  {(r.judge_score != null || r.judge_input_json) && (() => {
                    // 解析 Judge 输入 messages（可能为 null，老数据没有此字段）
                    let judgeMessages: Array<{role: string; content: string}> | null = null;
                    if (r.judge_input_json) {
                      try {
                        judgeMessages = JSON.parse(r.judge_input_json);
                      } catch {
                        judgeMessages = null;
                      }
                    }

                    // 构建 Judge 输出结构
                    const judgeOutput = r.judge_score != null ? {
                      score: r.judge_score,
                      reasoning: r.judge_reasoning,
                      risk_level_correct: r.risk_level_match === 1,
                      root_causes_covered: r.root_cause_match === 1,
                      has_hallucination: r.has_hallucination === 1,
                    } : null;

                    return (
                      <details className="group">
                        <summary className="cursor-pointer text-xs font-semibold text-slate-500 uppercase tracking-wider hover:text-blue-600 transition-colors flex items-center gap-1">
                          <span className="group-open:rotate-90 transition-transform">▶</span>
                          Judge Model 输入 / 输出详情
                        </summary>
                        <div className="mt-3 space-y-3">
                          {/* Judge 输入：System Prompt */}
                          {judgeMessages && judgeMessages.length > 0 && (
                            <div>
                              <h4 className="text-xs font-semibold text-violet-600 uppercase mb-1.5">📥 Judge 输入 — System Prompt</h4>
                              <div className="bg-violet-50 border border-violet-100 rounded-lg p-3 text-xs text-slate-700 whitespace-pre-wrap max-h-48 overflow-auto">
                                {judgeMessages.find(m => m.role === "system")?.content || "N/A"}
                              </div>
                            </div>
                          )}
                          {/* Judge 输入：User Prompt */}
                          {judgeMessages && judgeMessages.length > 1 && (
                            <div>
                              <h4 className="text-xs font-semibold text-blue-600 uppercase mb-1.5">📥 Judge 输入 — User Prompt</h4>
                              <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 text-xs text-slate-700 whitespace-pre-wrap max-h-64 overflow-auto">
                                {judgeMessages.find(m => m.role === "user")?.content || "N/A"}
                              </div>
                            </div>
                          )}
                          {/* 无 Judge 输入时的提示 */}
                          {!judgeMessages && (
                            <div className="text-xs text-slate-400 italic">
                              ⚠️ 此评测运行未记录 Judge 输入（在旧版本中执行），请重新运行评测以获取完整的 Judge 输入数据。
                            </div>
                          )}
                          {/* Judge 输出：结构化结果 */}
                          {judgeOutput && (
                            <div>
                              <h4 className="text-xs font-semibold text-emerald-600 uppercase mb-1.5">📤 Judge 输出 — 结构化评分结果</h4>
                              <div className="bg-emerald-50 border border-emerald-100 rounded-lg p-3 text-xs font-mono text-slate-700 whitespace-pre-wrap max-h-48 overflow-auto">
                                {JSON.stringify(judgeOutput, null, 2)}
                              </div>
                            </div>
                          )}
                        </div>
                      </details>
                    );
                  })()}

                  {/* Expected vs Actual 对比 */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">期望输出</h4>
                      <div className="bg-slate-50 rounded-lg p-3 text-xs font-mono overflow-auto max-h-64">
                        {expected ? (
                          <CompareJSON data={expected} compareWith={actual} mode="expected" />
                        ) : (
                          <span className="text-slate-400">无数据</span>
                        )}
                      </div>
                    </div>
                    <div>
                      <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">实际输出</h4>
                      <div className="bg-slate-50 rounded-lg p-3 text-xs font-mono overflow-auto max-h-64">
                        {actual ? (
                          <CompareJSON data={actual} compareWith={expected} mode="actual" />
                        ) : (
                          <span className="text-slate-400">无数据</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}

/** JSON 对比展示组件：高亮匹配/不匹配的字段 */
function CompareJSON({
  data,
  compareWith,
  mode,
}: {
  data: Record<string, unknown>;
  compareWith: Record<string, unknown> | null;
  mode: "expected" | "actual";
}) {
  return (
    <div className="space-y-1">
      {Object.entries(data).map(([key, value]) => {
        const otherValue = compareWith?.[key];
        const valueStr = typeof value === "object" ? JSON.stringify(value, null, 2) : String(value);
        const otherStr = otherValue != null ? (typeof otherValue === "object" ? JSON.stringify(otherValue) : String(otherValue)) : undefined;

        // 判断是否匹配
        let matchClass = "text-slate-600";
        if (compareWith && key in (compareWith || {})) {
          const match = JSON.stringify(value) === JSON.stringify(otherValue);
          if (mode === "actual") {
            matchClass = match ? "text-emerald-700 bg-emerald-50" : "text-red-700 bg-red-50";
          }
        }

        return (
          <div key={key} className={`rounded px-1 py-0.5 ${matchClass}`}>
            <span className="text-slate-400">{key}: </span>
            <span className="break-all">{valueStr.length > 200 ? valueStr.slice(0, 200) + "..." : valueStr}</span>
          </div>
        );
      })}
    </div>
  );
}
