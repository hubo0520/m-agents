/* API 客户端 — 封装所有后端 API 调用 */
import type {
  PaginatedResponse,
  RiskCaseListItem,
  CaseDetail,
  EvidenceItem,
  DashboardStats,
  ReviewRequest,
  EvalRunDetail,
  EvalDatasetDetail,
} from "@/types";
import { authFetch } from "./api-client";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  return authFetch<T>(path, options);
}

/* 看板指标 */
export async function getDashboardStats(): Promise<DashboardStats> {
  return fetchAPI<DashboardStats>("/api/dashboard/stats");
}

/* 案件列表 */
export async function getRiskCases(params: {
  risk_level?: string;
  status?: string;
  merchant_name?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: string;
}): Promise<PaginatedResponse<RiskCaseListItem>> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      searchParams.set(key, String(value));
    }
  });
  return fetchAPI<PaginatedResponse<RiskCaseListItem>>(
    `/api/risk-cases?${searchParams.toString()}`
  );
}

/* 案件详情 */
export async function getCaseDetail(caseId: number): Promise<CaseDetail> {
  return fetchAPI<CaseDetail>(`/api/risk-cases/${caseId}`);
}

/* 触发重新分析 */
export async function analyzeCase(
  caseId: number
): Promise<{ status: string; agent_output: unknown }> {
  return fetchAPI(`/api/risk-cases/${caseId}/analyze`, { method: "POST" });
}

/* 获取证据 */
export async function getEvidence(caseId: number): Promise<EvidenceItem[]> {
  return fetchAPI<EvidenceItem[]>(`/api/risk-cases/${caseId}/evidence`);
}

/* 审批案件 */
export async function reviewCase(
  caseId: number,
  req: ReviewRequest
): Promise<{ status: string; review_id: number; decision: string }> {
  return fetchAPI(`/api/risk-cases/${caseId}/review`, {
    method: "POST",
    body: JSON.stringify(req),
  });
}

/* 导出案件 */
export async function exportCase(
  caseId: number,
  format: "markdown" | "json"
): Promise<string | object> {
  const { getAccessToken } = await import("./auth");
  const token = getAccessToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(
    `${API_BASE}/api/risk-cases/${caseId}/export?format=${format}`,
    { headers }
  );
  if (!res.ok) throw new Error(`导出失败: ${res.status}`);
  if (format === "json") return res.json();
  return res.text();
}

/* ─────── V2: 任务管理 API ─────── */

import type {
  UnifiedTask,
  FinancingApplication,
  ClaimApplication,
  ManualReviewTask,
  TaskStatusUpdateRequest,
} from "@/types";

/* 统一任务列表 */
export async function getTasks(params: {
  task_type?: string;
  status?: string;
  assigned_to?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<UnifiedTask>> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      searchParams.set(key, String(value));
    }
  });
  return fetchAPI<PaginatedResponse<UnifiedTask>>(
    `/api/tasks?${searchParams.toString()}`
  );
}

/* 任务详情 */
export async function getTaskDetail(
  taskType: string,
  taskId: number
): Promise<FinancingApplication | ClaimApplication | ManualReviewTask> {
  return fetchAPI(`/api/tasks/${taskType}/${taskId}`);
}

/* 任务状态更新 */
export async function updateTaskStatus(
  taskType: string,
  taskId: number,
  req: TaskStatusUpdateRequest
): Promise<{ status: string; old_status: string; new_status: string }> {
  return fetchAPI(`/api/tasks/${taskType}/${taskId}/status`, {
    method: "PUT",
    body: JSON.stringify(req),
  });
}

/* 手动生成融资申请 */
export async function generateFinancing(
  caseId: number,
  data?: { merchant_id?: number; amount_requested?: number; reason?: string }
): Promise<{ status: string; application_id: number; message: string }> {
  return fetchAPI(`/api/risk-cases/${caseId}/generate-financing-application`, {
    method: "POST",
    body: JSON.stringify(data || {}),
  });
}

/* 手动生成理赔申请 */
export async function generateClaim(
  caseId: number,
  data?: { merchant_id?: number; claim_amount?: number; claim_reason?: string }
): Promise<{ status: string; claim_id: number; message: string }> {
  return fetchAPI(`/api/risk-cases/${caseId}/generate-claim-application`, {
    method: "POST",
    body: JSON.stringify(data || {}),
  });
}

/* 手动生成复核任务 */
export async function generateReview(
  caseId: number,
  data?: { merchant_id?: number; task_type?: string; evidence_ids?: number[] }
): Promise<{ status: string; review_id: number; message: string }> {
  return fetchAPI(`/api/risk-cases/${caseId}/generate-manual-review`, {
    method: "POST",
    body: JSON.stringify(data || {}),
  });
}

/* 获取案件关联的执行任务 */
export async function getCaseTasks(
  caseId: number
): Promise<UnifiedTask[]> {
  return fetchAPI<UnifiedTask[]>(`/api/risk-cases/${caseId}/tasks`);
}

/* 获取分析进度（刷新页面后恢复工作流面板） */
export async function getAnalysisProgress(
  caseId: number
): Promise<{ status: string; progress: Array<{
  step: string;
  step_name: string;
  step_index: number;
  total_steps: number;
  status: string;
  elapsed_ms: number;
  summary: string;
  llm_input_summary?: string;
  llm_output_summary?: string;
}> }> {
  return fetchAPI(`/api/risk-cases/${caseId}/analysis-progress`);
}

/* ─────── V3: 工作流 API ─────── */

import type {
  WorkflowRun,
  ApprovalTask,
  WorkflowTrace,
  PromptVersionItem,
  EvalDatasetItem,
  EvalRunItem,
  AgentConfig,
} from "@/types";

/* 启动工作流 */
export async function startWorkflow(caseId: number): Promise<{ workflow_run_id: number; status: string }> {
  return fetchAPI("/api/workflows/start", {
    method: "POST",
    body: JSON.stringify({ case_id: caseId }),
  });
}

/* 恢复工作流 */
export async function resumeWorkflow(runId: number): Promise<{ workflow_run_id: number; status: string }> {
  return fetchAPI(`/api/workflows/${runId}/resume`, { method: "POST" });
}

/* 重试工作流 */
export async function retryWorkflow(runId: number): Promise<{ workflow_run_id: number; status: string }> {
  return fetchAPI(`/api/workflows/${runId}/retry`, { method: "POST" });
}

/* 获取工作流详情 */
export async function getWorkflowRun(runId: number): Promise<WorkflowRun> {
  return fetchAPI<WorkflowRun>(`/api/workflows/${runId}`);
}

/* 获取工作流轨迹 */
export async function getWorkflowTrace(runId: number): Promise<WorkflowTrace> {
  return fetchAPI<WorkflowTrace>(`/api/workflows/${runId}/trace`);
}

/* 获取工作流列表 */
export async function getWorkflows(params: {
  status?: string;
  case_id?: number;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<WorkflowRun>> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") searchParams.set(key, String(value));
  });
  return fetchAPI<PaginatedResponse<WorkflowRun>>(`/api/workflows?${searchParams.toString()}`);
}

/* 获取案件最新 run */
export async function getLatestRun(caseId: number): Promise<WorkflowRun> {
  return fetchAPI<WorkflowRun>(`/api/cases/${caseId}/latest-run`);
}

/* 重开案件 */
export async function reopenCase(caseId: number): Promise<{ status: string; case_id: number }> {
  return fetchAPI(`/api/cases/${caseId}/reopen`, { method: "POST" });
}

/* ─────── V3: 审批 API ─────── */

/* 获取审批列表 */
export async function getApprovals(params: {
  status?: string;
  approval_type?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<ApprovalTask>> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") searchParams.set(key, String(value));
  });
  return fetchAPI<PaginatedResponse<ApprovalTask>>(`/api/approvals?${searchParams.toString()}`);
}

/* 获取审批详情 */
export async function getApprovalDetail(approvalId: number): Promise<ApprovalTask> {
  return fetchAPI<ApprovalTask>(`/api/approvals/${approvalId}`);
}

/* 批准 */
export async function approveTask(approvalId: number, data: { reviewer_id: string; comment: string }): Promise<{ status: string }> {
  return fetchAPI(`/api/approvals/${approvalId}/approve`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/* 驳回 */
export async function rejectTask(approvalId: number, data: { reviewer_id: string; comment: string }): Promise<{ status: string }> {
  return fetchAPI(`/api/approvals/${approvalId}/reject`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/* 修改后批准 */
export async function reviseAndApprove(approvalId: number, data: { reviewer_id: string; comment: string; revised_payload: unknown }): Promise<{ status: string }> {
  return fetchAPI(`/api/approvals/${approvalId}/revise-and-approve`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/* 批量审批 */
export async function batchApprove(data: { approval_ids: number[]; action: string; reviewer_id: string; comment: string }): Promise<{ results: unknown[] }> {
  return fetchAPI("/api/approvals/batch", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/* ─────── V3: 配置 API ─────── */

/* 获取 Agent 配置 */
export async function getAgentConfigs(): Promise<{ configs: AgentConfig[] }> {
  return fetchAPI("/api/agent-configs");
}

/* 获取 Prompt 版本列表 */
export async function getPromptVersions(agentName?: string): Promise<{ items: PromptVersionItem[] }> {
  const params = agentName ? `?agent_name=${agentName}` : "";
  return fetchAPI(`/api/prompt-versions${params}`);
}

/* 创建 Prompt 版本 */
export async function createPromptVersion(data: { agent_name: string; content: string; canary_weight?: number }): Promise<{ id: number; version: string }> {
  return fetchAPI("/api/prompt-versions", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/* 创建 Schema 版本 */
export async function createSchemaVersion(data: { agent_name: string; json_schema: string }): Promise<{ id: number; version: string }> {
  return fetchAPI("/api/schema-versions", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/* 创建模型策略 */
export async function createModelPolicy(data: { agent_name: string; model_name: string; temperature?: number; max_tokens?: number }): Promise<{ status: string }> {
  return fetchAPI("/api/model-policies", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/* ─────── V3: 评测 API ─────── */

/* 获取评测数据集列表 */
export async function getEvalDatasets(): Promise<{ items: EvalDatasetItem[] }> {
  return fetchAPI("/api/evals/datasets");
}

/* 创建评测数据集 */
export async function createEvalDataset(data: { name: string; description?: string; test_cases: unknown[] }): Promise<{ id: number }> {
  return fetchAPI("/api/evals/datasets", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/* 获取评测运行列表 */
export async function getEvalRuns(): Promise<{ items: EvalRunItem[] }> {
  return fetchAPI("/api/evals/runs");
}

/* 创建评测运行 */
export async function createEvalRun(data: { dataset_id: number; model_name?: string; prompt_version?: string; reuse_existing?: boolean }): Promise<EvalRunItem> {
  return fetchAPI("/api/evals/runs", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/* 获取评测运行详情 */
export async function getEvalRun(evalRunId: number): Promise<EvalRunDetail> {
  return fetchAPI(`/api/evals/runs/${evalRunId}`);
}

/* 获取数据集详情（含测试用例） */
export async function getEvalDataset(datasetId: number): Promise<EvalDatasetDetail> {
  return fetchAPI(`/api/evals/datasets/${datasetId}`);
}

/* 更新数据集 */
export async function updateEvalDataset(datasetId: number, data: { name?: string; description?: string; test_cases?: unknown[] }): Promise<{ id: number }> {
  return fetchAPI(`/api/evals/datasets/${datasetId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

/* 从线上案件导入为数据集 */
export async function importCasesToDataset(data: { case_ids: number[]; dataset_name: string; description?: string }): Promise<{ id: number; test_case_count: number }> {
  return fetchAPI("/api/evals/datasets/import-from-cases", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/* ─────── V4: 对话式分析 API ─────── */

export interface ConversationItem {
  id: number;
  case_id: number;
  title: string;
  message_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface ConversationMessageItem {
  id: number;
  conversation_id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string | null;
}

/* 创建对话会话 */
export async function createConversation(
  caseId: number,
  title?: string
): Promise<{ id: number; case_id: number; title: string; created_at: string | null }> {
  return fetchAPI(`/api/cases/${caseId}/conversations`, {
    method: "POST",
    body: JSON.stringify({ title: title || "新对话" }),
  });
}

/* 获取案件对话列表 */
export async function getConversations(caseId: number): Promise<ConversationItem[]> {
  return fetchAPI<ConversationItem[]>(`/api/cases/${caseId}/conversations`);
}

/* 获取对话消息列表 */
export async function getMessages(conversationId: number): Promise<ConversationMessageItem[]> {
  return fetchAPI<ConversationMessageItem[]>(`/api/conversations/${conversationId}/messages`);
}

/* ─────── V4: 可观测面板 API ─────── */

export interface ObservabilitySummary {
  today_analysis_count: number;
  today_change_pct: number;
  avg_latency_ms: number;
  llm_success_rate: number;
  total_agent_runs: number;
  degradation_count: number;
  days: number;
}

export interface LatencyTrendResponse {
  trend: Array<{ date: string; avg_latency_ms: number; count: number }>;
  days: number;
}

export interface AgentLatencyResponse {
  agents: Array<{ agent_name: string; avg_latency_ms: number; count: number }>;
  days: number;
}

export interface WorkflowStatusResponse {
  statuses: Array<{ status: string; count: number; percentage: number }>;
  total: number;
  days: number;
}

/* 获取可观测概览指标 */
export async function getObservabilitySummary(days: number = 7): Promise<ObservabilitySummary> {
  return fetchAPI<ObservabilitySummary>(`/api/observability/summary?days=${days}`);
}

/* 获取响应时间趋势 */
export async function getLatencyTrend(days: number = 7): Promise<LatencyTrendResponse> {
  return fetchAPI<LatencyTrendResponse>(`/api/observability/latency-trend?days=${days}`);
}

/* 获取各 Agent 平均耗时 */
export async function getAgentLatency(days: number = 7): Promise<AgentLatencyResponse> {
  return fetchAPI<AgentLatencyResponse>(`/api/observability/agent-latency?days=${days}`);
}

/* 获取工作流状态分布 */
export async function getWorkflowStatusDist(days: number = 7): Promise<WorkflowStatusResponse> {
  return fetchAPI<WorkflowStatusResponse>(`/api/observability/workflow-status?days=${days}`);
}
