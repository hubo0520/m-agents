/* TypeScript 类型定义 */

export interface MerchantInfo {
  id: number;
  name: string;
  industry: string;
  settlement_cycle_days: number;
  store_level: string;
}

export interface RiskCaseListItem {
  id: number;
  merchant_id: number;
  merchant_name: string;
  industry: string;
  risk_score: number | null;
  risk_level: string;
  status: string;
  return_rate_7d: number | null;
  baseline_return_rate: number | null;
  return_amplification: number | null;
  predicted_gap: number | null;
  recommendation_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface EvidenceItem {
  id: number;
  evidence_type: string;
  source_table: string | null;
  source_id: number | null;
  summary: string | null;
  importance_score: number | null;
}

export interface AuditLog {
  id: number;
  entity_type: string;
  entity_id: number;
  actor: string | null;
  action: string;
  old_value: string | null;
  new_value: string | null;
  created_at: string | null;
}

export interface TrendDataPoint {
  date: string;
  order_amount: number;
  return_rate: number;
  refund_amount: number;
  settlement_amount: number;
}

export interface RootCause {
  label: string;
  explanation: string;
  confidence: number;
  evidence_ids: string[];
}

export interface CashGapForecast {
  horizon_days: number;
  predicted_gap: number;
  lowest_cash_day: string | null;
  confidence: number;
  daily_forecast?: DailyForecast[];
}

export interface DailyForecast {
  date: string;
  inflow: number;
  outflow: number;
  netflow: number;
}

export interface ExpectedBenefit {
  cash_relief?: number | null;
  time_horizon_days?: number | null;
  description: string;
}

export interface ActionRecommendation {
  id?: number;
  action_type: string;
  title: string;
  why: string;
  expected_benefit: string | ExpectedBenefit;
  confidence: number;
  requires_manual_review: boolean;
  evidence_ids: string[];
  db_requires_manual_review?: boolean;
}

export interface AgentOutput {
  case_id: string;
  risk_level: string;
  case_summary: string;
  root_causes: RootCause[];
  cash_gap_forecast: CashGapForecast;
  recommendations: ActionRecommendation[];
  manual_review_required: boolean;
}

export interface ReviewItem {
  id: number;
  reviewer_id: string;
  decision: string;
  comment: string;
  final_action_json: unknown;
  created_at: string | null;
}

export interface CaseDetail {
  id: number;
  merchant: MerchantInfo;
  risk_score: number | null;
  risk_level: string;
  status: string;
  trigger_json: unknown;
  agent_output: AgentOutput | null;
  metrics: Record<string, number> | null;
  trend_data: TrendDataPoint[] | null;
  forecast: CashGapForecast | null;
  evidence: EvidenceItem[];
  recommendations: ActionRecommendation[];
  reviews: ReviewItem[];
  audit_logs: AuditLog[];
  created_at: string | null;
  updated_at: string | null;
}

export interface DashboardStats {
  merchant_count: number;
  new_high_risk_count: number;
  total_predicted_gap: number;
  avg_settlement_delay: number;
}

export interface ReviewRequest {
  decision: string;
  comment: string;
  final_actions?: unknown[];
  reviewer_id?: string;
}

/* ─────── V2: 执行任务类型定义 ─────── */

export interface FinancingApplication {
  id: number;
  task_type: "financing";
  merchant_id: number;
  merchant_name: string;
  case_id: number;
  case_risk_level: string | null;
  recommendation_id: number | null;
  amount_requested: number;
  loan_purpose: string | null;
  repayment_plan: RepaymentPlan | null;
  merchant_info_snapshot: MerchantSnapshot | null;
  historical_settlement: HistoricalSettlement | null;
  approval_status: string;
  reviewer_comment: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface RepaymentPlan {
  total_amount: number;
  term_months: number;
  monthly_payment: number;
  interest_rate: number;
  schedule: { month: number; payment: number }[];
}

export interface MerchantSnapshot {
  merchant_id: number;
  merchant_name: string;
  industry: string;
  store_level: string;
  settlement_cycle_days: number;
  total_sales_90d: number;
  total_returns_90d: number;
  snapshot_time: string;
}

export interface HistoricalSettlement {
  period: string;
  total_settlement_count: number;
  settled_count: number;
  delayed_count: number;
  total_amount: number;
  avg_delay_days: number;
  delay_rate: number;
}

export interface ClaimApplication {
  id: number;
  task_type: "claim";
  merchant_id: number;
  merchant_name: string;
  case_id: number;
  case_risk_level: string | null;
  recommendation_id: number | null;
  policy_id: number | null;
  claim_amount: number;
  claim_reason: string | null;
  evidence_snapshot: unknown[] | null;
  return_details: ReturnDetails | null;
  claim_status: string;
  reviewer_comment: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ReturnDetails {
  period: string;
  return_count: number;
  total_refund_amount: number;
  reason_distribution: Record<string, number>;
}

export interface ManualReviewTask {
  id: number;
  task_type: "manual_review";
  merchant_id: number;
  merchant_name: string;
  case_id: number;
  case_risk_level: string | null;
  recommendation_id: number | null;
  task_type_detail: string;
  review_reason: string | null;
  evidence_ids: number[];
  assigned_to: string | null;
  status: string;
  review_result: string | null;
  reviewer_comment: string | null;
  created_at: string | null;
  updated_at: string | null;
  completed_at: string | null;
}

export interface UnifiedTask {
  task_id: number;
  task_type: "financing" | "claim" | "manual_review";
  merchant_id: number;
  merchant_name: string;
  case_id: number;
  status: string;
  amount: number | null;
  assigned_to: string | null;
  created_at: string | null;
}

export interface TaskStatusUpdateRequest {
  new_status: string;
  comment: string;
  reviewer_id: string;
}

/* ─────── V3: 多 Agent 生产化类型定义 ─────── */

export interface WorkflowRun {
  id: number;
  case_id: number;
  graph_version: string;
  status: string;
  current_node: string | null;
  started_at: string | null;
  updated_at: string | null;
  paused_at: string | null;
  resumed_at: string | null;
  ended_at: string | null;
  agent_runs?: AgentRunItem[];
}

export interface AgentRunItem {
  id: number;
  workflow_run_id: number;
  agent_name: string;
  model_name: string | null;
  prompt_version: string | null;
  schema_version: string | null;
  status: string;
  latency_ms: number | null;
  input_json: string | null;
  output_json: string | null;
  created_at: string | null;
}

export interface ApprovalTask {
  id: number;
  workflow_run_id: number | null;
  case_id: number;
  approval_type: string;
  assignee_role: string | null;
  status: string;
  payload_json: string | null;
  reviewer: string | null;
  reviewed_at: string | null;
  comment: string | null;
  final_action_json: string | null;
  created_at: string | null;
  due_at: string | null;
}

export interface ToolInvocationItem {
  id: number;
  workflow_run_id: number | null;
  tool_name: string;
  tool_version: string | null;
  status: string;
  created_at: string | null;
}

export interface PromptVersionItem {
  id: number;
  agent_name: string;
  version: string;
  status: string;
  canary_weight: number | null;
  created_at: string | null;
}

export interface SchemaVersionItem {
  id: number;
  agent_name: string;
  version: string;
  created_at: string | null;
}

export interface EvalDatasetItem {
  id: number;
  name: string;
  description: string | null;
  test_case_count: number;
  created_at: string | null;
}

export interface EvalRunItem {
  id: number;
  dataset_id: number;
  model_name: string;
  status: string;
  adoption_rate: number | null;
  rejection_rate: number | null;
  evidence_coverage_rate: number | null;
  schema_pass_rate: number | null;
  hallucination_rate: number | null;
  started_at: string | null;
  ended_at: string | null;
}

export interface EvalResultItem {
  test_case_index: number;
  adopted: number | null;
  has_hallucination: number | null;
  schema_valid: number | null;
  evidence_covered: number | null;
}

export interface WorkflowTrace {
  workflow_run_id: number;
  case_id: number;
  status: string;
  nodes: AgentRunItem[];
  total_latency_ms: number;
}

export interface AgentConfig {
  agent_name: string;
  active_prompt_version: string | null;
  latest_schema_version: string | null;
  model_name: string;
}
