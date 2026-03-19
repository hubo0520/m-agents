"use client";

import { useState, useEffect, useRef } from "react";
import type { AnalysisProgressEvent } from "@/lib/sse";
import LlmDetailPanel, { type LlmStepData } from "./LlmDetailPanel";

/** 步骤状态 */
export type StepStatus = "pending" | "running" | "completed" | "error";

/** 单个步骤 */
export interface WorkflowStep {
  step: string;
  step_name: string;
  status: StepStatus;
  elapsed_ms?: number;
  summary?: string;
  llm_input_summary?: string;
  llm_output_summary?: string;
}

/** 使用 LLM 的步骤集合 */
const LLM_STEPS = new Set([
  "diagnose_case",
  "generate_recommendations",
  "finalize_summary",
  "run_guardrails",
  "generate_summary",  // V1/V2
]);

interface AnalysisWorkflowPanelProps {
  steps: WorkflowStep[];
  isComplete: boolean;
  error?: string | null;
  /** 每个 LLM 步骤的交互数据（key 为 step 名称） */
  llmData?: Record<string, LlmStepData>;
}

/**
 * 分析工作流可视化面板
 *
 * 垂直 Stepper 布局，展示 Agent 分析的各阶段进度
 */
export default function AnalysisWorkflowPanel({
  steps,
  isComplete,
  error,
  llmData,
}: AnalysisWorkflowPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  // 当 llmData 变化时（如页面刷新恢复），自动展开有 LLM 数据的步骤
  useEffect(() => {
    if (!llmData) return;
    const keysWithData = Object.keys(llmData).filter(
      (k) => llmData[k] && (llmData[k].systemPrompt || llmData[k].fullContent || llmData[k].streamingContent || llmData[k].isStreaming)
    );
    if (keysWithData.length > 0) {
      setExpandedSteps((prev) => {
        const next = new Set(prev);
        let changed = false;
        for (const k of keysWithData) {
          if (!next.has(k)) {
            next.add(k);
            changed = true;
          }
        }
        return changed ? next : prev;
      });
    }
  }, [llmData]);

  const toggleExpand = (step: string) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(step)) {
        next.delete(step);
      } else {
        next.add(step);
      }
      return next;
    });
  };

  // 自动滚动到当前进行中的步骤
  useEffect(() => {
    const runningStep = document.querySelector('[data-step-status="running"]');
    if (runningStep) {
      runningStep.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [steps]);

  return (
    <div
      ref={panelRef}
      className={`transition-opacity duration-500 ${isComplete ? "opacity-0" : "opacity-100"}`}
    >
      <div className="flex items-center gap-2 mb-4">
        <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
        <h3 className="text-sm font-semibold text-slate-700">Agent 分析中</h3>
        {steps.length > 0 && (
          <span className="text-xs text-slate-400 ml-auto">
            {steps.filter((s) => s.status === "completed").length}/{steps.length}
          </span>
        )}
      </div>

      {/* 无步骤数据时（刷新页面恢复场景）显示等待状态 */}
      {steps.length === 0 && !error && (
        <div className="flex flex-col items-center py-6 gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-slate-200 border-t-blue-500 animate-spin" />
          <p className="text-sm text-slate-500">分析进行中，等待结果...</p>
          <p className="text-xs text-slate-400">页面将在分析完成后自动刷新</p>
        </div>
      )}

      <div className="relative">
        {steps.map((step, index) => {
          const isLlmStep = LLM_STEPS.has(step.step);
          const stepLlmData = llmData?.[step.step];
          const hasLlmData = !!stepLlmData && (
            !!stepLlmData.systemPrompt ||
            !!stepLlmData.userPrompt ||
            !!stepLlmData.streamingContent ||
            !!stepLlmData.fullContent ||
            !!stepLlmData.isStreaming
          );
          const isExpanded = expandedSteps.has(step.step);

          return (
          <div
            key={step.step}
            data-step-status={step.status}
            className="flex gap-3 mb-0.5 last:mb-0"
          >
            {/* 左侧：图标 + 连接线 */}
            <div className="flex flex-col items-center w-6 flex-shrink-0">
              <StepIcon status={step.status} />
              {index < steps.length - 1 && (
                <div
                  className={`w-px flex-1 min-h-[16px] transition-colors duration-300 ${
                    step.status === "completed"
                      ? "bg-green-300"
                      : step.status === "error"
                      ? "bg-red-300"
                      : "bg-slate-200"
                  }`}
                />
              )}
            </div>

            {/* 右侧：内容 */}
            <div className={`flex-1 pb-3 transition-all duration-300 ${
              step.status === "running" ? "translate-x-0 opacity-100" : ""
            }`}>
              <div
                className={`flex items-center gap-2 ${
                  isLlmStep && hasLlmData ? "cursor-pointer hover:opacity-80" : ""
                }`}
                onClick={() => {
                  if (isLlmStep && hasLlmData) toggleExpand(step.step);
                }}
              >
                <span
                  className={`text-sm font-medium transition-colors duration-300 ${
                    step.status === "completed"
                      ? "text-green-700"
                      : step.status === "running"
                      ? "text-blue-700"
                      : step.status === "error"
                      ? "text-red-700"
                      : "text-slate-400"
                  }`}
                >
                  {step.step_name}
                </span>

                {/* LLM 步骤的 AI 标签 */}
                {isLlmStep && (step.status === "running" || step.status === "completed") && (
                  <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-violet-50 border border-violet-200">
                    <svg className="w-2.5 h-2.5 text-violet-500" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
                    </svg>
                    <span className="text-[9px] font-semibold text-violet-600 uppercase">AI</span>
                  </span>
                )}

                {/* 展开/折叠图标 */}
                {isLlmStep && hasLlmData && (
                  <svg
                    className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${
                      isExpanded ? "rotate-180" : ""
                    }`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                )}

                {step.status === "completed" && step.elapsed_ms !== undefined && (
                  <span className="text-xs text-slate-400 tabular-nums ml-auto">
                    {step.elapsed_ms >= 1000
                      ? `${(step.elapsed_ms / 1000).toFixed(1)}s`
                      : `${step.elapsed_ms}ms`}
                  </span>
                )}
              </div>

              {/* 摘要 — 完成后 slide-down 显示 */}
              {step.status === "completed" && step.summary && (
                <p className="text-xs text-slate-500 mt-0.5 animate-slide-down">
                  {step.summary}
                </p>
              )}

              {/* 错误信息 */}
              {step.status === "error" && step.summary && (
                <p className="text-xs text-red-500 mt-0.5 animate-slide-down">
                  ❌ {step.summary}
                </p>
              )}

              {/* LLM 交互详情面板 */}
              {isLlmStep && stepLlmData && (
                <LlmDetailPanel
                  data={stepLlmData}
                  isExpanded={isExpanded || (step.status === "running" && stepLlmData.isStreaming)}
                />
              )}
            </div>
          </div>
          );
        })}
      </div>

      {/* 全局错误提示 */}
      {error && (
        <div className="mt-3 p-2.5 bg-red-50 border border-red-200 rounded-lg animate-fade-in">
          <p className="text-xs text-red-600">{error}</p>
        </div>
      )}
    </div>
  );
}

/** 步骤图标 */
function StepIcon({ status }: { status: StepStatus }) {
  switch (status) {
    case "completed":
      return (
        <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center animate-scale-in">
          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
      );
    case "running":
      return (
        <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center step-pulse">
          <div className="w-2 h-2 rounded-full bg-white" />
        </div>
      );
    case "error":
      return (
        <div className="w-5 h-5 rounded-full bg-red-500 flex items-center justify-center animate-scale-in">
          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
      );
    default:
      return (
        <div className="w-5 h-5 rounded-full border-2 border-slate-200 bg-white" />
      );
  }
}


/**
 * 从 SSE 进度事件生成初始步骤列表
 * 当收到第一个 progress 事件时，根据 total_steps 初始化所有步骤
 */
export function initStepsFromEvent(event: AnalysisProgressEvent): WorkflowStep[] {
  // 定义所有可能的步骤名称映射（覆盖 V1/V2 和 V3）
  const V1V2_STEPS: [string, string][] = [
    ["compute_metrics", "计算商家指标"],
    ["forecast_gap", "现金缺口预测"],
    ["collect_evidence", "收集证据"],
    ["generate_summary", "生成摘要"],
    ["generate_recommendations", "生成建议"],
    ["guardrail_check", "守卫校验"],
    ["save_results", "保存分析结果"],
  ];

  const V3_STEPS: [string, string][] = [
    ["load_case_context", "加载案件上下文"],
    ["triage_case", "案件分诊"],
    ["compute_metrics", "计算商家指标"],
    ["forecast_gap", "现金缺口预测"],
    ["collect_evidence", "收集证据"],
    ["diagnose_case", "诊断根因"],
    ["generate_recommendations", "生成建议"],
    ["run_guardrails", "合规校验"],
    ["finalize_summary", "生成分析总结"],
    ["create_approval_tasks", "创建审批任务"],
    ["write_audit_log", "写入审计日志"],
  ];

  // 根据 total_steps 判断是 V1/V2 还是 V3
  const steps = event.total_steps <= 7 ? V1V2_STEPS : V3_STEPS;

  return steps.slice(0, event.total_steps).map(([step, name], idx) => ({
    step,
    step_name: name,
    status: "pending" as StepStatus,
  }));
}

/**
 * 更新步骤状态（根据进度事件）
 */
export function updateStepFromEvent(
  steps: WorkflowStep[],
  event: AnalysisProgressEvent
): WorkflowStep[] {
  return steps.map((s, idx) => {
    if (idx === event.step_index - 1) {
      return {
        ...s,
        status: event.status as StepStatus,
        elapsed_ms: event.elapsed_ms,
        summary: event.summary,
      };
    }
    return s;
  });
}

/**
 * 从后端持久化进度数据恢复步骤列表
 * 用于刷新页面后恢复工作流面板
 */
export function buildStepsFromProgress(
  progress: Array<{
    step: string;
    step_name: string;
    step_index: number;
    total_steps: number;
    status: string;
    elapsed_ms: number;
    summary: string;
    llm_input_summary?: string;
    llm_output_summary?: string;
  }>,
  totalSteps: number
): WorkflowStep[] {
  const V1V2_STEPS: [string, string][] = [
    ["compute_metrics", "计算商家指标"],
    ["forecast_gap", "现金缺口预测"],
    ["collect_evidence", "收集证据"],
    ["generate_summary", "生成摘要"],
    ["generate_recommendations", "生成建议"],
    ["guardrail_check", "守卫校验"],
    ["save_results", "保存分析结果"],
  ];

  const V3_STEPS: [string, string][] = [
    ["load_case_context", "加载案件上下文"],
    ["triage_case", "案件分诊"],
    ["compute_metrics", "计算商家指标"],
    ["forecast_gap", "现金缺口预测"],
    ["collect_evidence", "收集证据"],
    ["diagnose_case", "诊断根因"],
    ["generate_recommendations", "生成建议"],
    ["run_guardrails", "合规校验"],
    ["finalize_summary", "生成分析总结"],
    ["create_approval_tasks", "创建审批任务"],
    ["write_audit_log", "写入审计日志"],
  ];

  // 根据 totalSteps 判断模式
  const stepDefs = totalSteps <= 7 ? V1V2_STEPS : V3_STEPS;

  // 构建进度 map
  const progressMap = new Map(progress.map((p) => [p.step, p]));

  return stepDefs.slice(0, totalSteps).map(([step, name]) => {
    const p = progressMap.get(step);
    if (p) {
      return {
        step,
        step_name: p.step_name || name,
        status: p.status as StepStatus,
        elapsed_ms: p.elapsed_ms,
        summary: p.summary,
        llm_input_summary: p.llm_input_summary,
        llm_output_summary: p.llm_output_summary,
      };
    }
    return {
      step,
      step_name: name,
      status: "pending" as StepStatus,
    };
  });
}
