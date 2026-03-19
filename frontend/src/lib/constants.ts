// 案件状态映射（含颜色 + 中文标签）
export const CASE_STATUS_MAP: Record<string, { label: string; color: string }> = {
  NEW:               { label: "新建",       color: "bg-blue-100 text-blue-700" },
  TRIAGED:           { label: "已分诊",     color: "bg-indigo-100 text-indigo-800" },
  ANALYZING:         { label: "分析中",     color: "bg-purple-100 text-purple-700" },
  RECOMMENDING:      { label: "建议生成中", color: "bg-violet-100 text-violet-800" },
  PENDING_APPROVAL:  { label: "待审批",     color: "bg-yellow-100 text-yellow-800" },
  BLOCKED_BY_GUARD:  { label: "合规拦截",   color: "bg-orange-100 text-orange-800" },
  APPROVED:          { label: "已通过",     color: "bg-green-100 text-green-700" },
  EXECUTING:         { label: "执行中",     color: "bg-cyan-100 text-cyan-800" },
  WAITING_CALLBACK:  { label: "等待回调",   color: "bg-teal-100 text-teal-800" },
  COMPLETED:         { label: "已完成",     color: "bg-green-100 text-green-800" },
  PAUSED:            { label: "已暂停",     color: "bg-orange-100 text-orange-800" },
  RESUMED:           { label: "已恢复",     color: "bg-blue-100 text-blue-800" },
  PENDING_REVIEW:    { label: "待审核",     color: "bg-orange-100 text-orange-700" },
  ANALYZED:          { label: "已分析",     color: "bg-purple-100 text-purple-700" },
  REJECTED:          { label: "已驳回",     color: "bg-red-100 text-red-700" },
  REVIEWED:          { label: "已审阅",     color: "bg-green-100 text-green-700" },
  FAILED_RETRYABLE:  { label: "失败可重试", color: "bg-red-100 text-red-700" },
  FAILED_FINAL:      { label: "最终失败",   color: "bg-red-200 text-red-900" },
};

// 任务状态映射
export const TASK_STATUS_MAP: Record<string, { label: string; color: string }> = {
  DRAFT:          { label: "草稿",   color: "bg-gray-100 text-gray-600" },
  PENDING:        { label: "待处理", color: "bg-yellow-100 text-yellow-700" },
  PENDING_REVIEW: { label: "待审核", color: "bg-amber-100 text-amber-700" },
  IN_PROGRESS:    { label: "进行中", color: "bg-blue-100 text-blue-700" },
  EXECUTING:      { label: "执行中", color: "bg-cyan-100 text-cyan-700" },
  APPROVED:       { label: "已通过", color: "bg-green-100 text-green-700" },
  REJECTED:       { label: "已驳回", color: "bg-red-100 text-red-700" },
  COMPLETED:      { label: "已完成", color: "bg-green-100 text-green-700" },
  CLOSED:         { label: "已关闭", color: "bg-gray-100 text-gray-600" },
};

// Agent 中文名映射
export const AGENT_NAME_MAP: Record<string, string> = {
  // 工作流节点名称
  load_case_context:        "案件加载",
  triage_case:              "案件分诊",
  compute_metrics:          "指标计算",
  forecast_gap:             "现金流预测",
  collect_evidence:         "证据收集",
  diagnose_case:            "风险诊断",
  generate_recommendations: "动作建议",
  run_guardrails:           "合规校验",
  create_approval_tasks:    "审批创建",
  execute_actions:          "动作执行",
  wait_for_approval:        "等待审批",
  wait_external_callback:   "等待外部回调",
  finalize_summary:         "案件总结",
  write_audit_log:          "审计记录",
  // Agent 配置名称（设置页 Prompt/Schema 管理）
  triage_agent:             "分诊 Agent",
  diagnosis_agent:          "诊断 Agent",
  forecast_agent:           "预测 Agent",
  recommendation_agent:     "建议 Agent",
  evidence_agent:           "证据 Agent",
  compliance_guard_agent:   "合规 Agent",
  execution_agent:          "执行 Agent",
  summary_agent:            "总结 Agent",
};

// 证据类型映射
export const EVIDENCE_TYPE_MAP: Record<string, string> = {
  order:         "订单数据",
  return:        "退货数据",
  logistics:     "物流数据",
  settlement:    "结算数据",
  rule_hit:      "规则命中",
  product_match: "商品匹配",
};

// 审批角色映射
export const ROLE_NAME_MAP: Record<string, string> = {
  finance_ops: "财务运营",
  risk_ops:    "风控运营",
  claim_ops:   "理赔运营",
};

// 审批类型映射
export const APPROVAL_TYPE_MAP: Record<string, string> = {
  business_loan:      "经营贷",
  advance_settlement: "回款加速",
  fraud_review:       "反欺诈复核",
  claim_submission:   "理赔提交",
  manual_handoff:     "人工接管",
};

// 审批状态映射
export const APPROVAL_STATUS_MAP: Record<string, { label: string; color: string }> = {
  PENDING:  { label: "待审批", color: "bg-yellow-100 text-yellow-800" },
  APPROVED: { label: "已批准", color: "bg-green-100 text-green-800" },
  REJECTED: { label: "已驳回", color: "bg-red-100 text-red-800" },
  OVERDUE:  { label: "已超时", color: "bg-orange-100 text-orange-800" },
};

// 审计操作映射
export const AUDIT_ACTION_MAP: Record<string, string> = {
  status_change:              "状态变更",
  review_approve:             "审批通过",
  review_approve_with_changes:"修改后通过",
  review_reject:              "审批驳回",
  task_generation_triggered:  "任务自动生成",
  task_generation_failed:     "任务生成失败",
  workflow_completed:         "工作流完成",
  manual_handoff_created:     "人工接管创建",
};

export function getAuditActionLabel(action: string): string {
  return AUDIT_ACTION_MAP[action] ?? action;
}

/** 将审计日志的 value 解析为可读的中文片段数组 [{label, value}] */
export function parseAuditValue(raw: string | null | undefined): { label: string; value: string }[] {
  if (!raw) return [];

  // 尝试 JSON 解析
  try {
    const obj = JSON.parse(raw);
    if (typeof obj !== "object" || obj === null) {
      return [{ label: "", value: raw }];
    }

    const FIELD_LABELS: Record<string, string> = {
      status:   "状态",
      decision: "决定",
      comment:  "备注",
      case_id:  "案件ID",
      summary:  "总结",
      failed_node: "失败节点",
      error:    "错误",
    };

    const DECISION_LABELS: Record<string, string> = {
      approve:              "通过",
      approve_with_changes: "修改后通过",
      reject:               "驳回",
    };

    const result: { label: string; value: string }[] = [];
    for (const [key, val] of Object.entries(obj)) {
      const label = FIELD_LABELS[key] ?? key;
      let displayVal = String(val);

      if (key === "status") {
        displayVal = getCaseStatusLabel(displayVal);
      } else if (key === "decision") {
        displayVal = DECISION_LABELS[displayVal] ?? displayVal;
      } else if (key === "failed_node") {
        displayVal = getAgentName(displayVal);
      }

      // 跳过空备注
      if (key === "comment" && (!val || String(val).trim() === "")) continue;

      result.push({ label, value: displayVal });
    }
    return result;
  } catch {
    // 非 JSON，可能是纯状态文本
    const statusLabel = getCaseStatusLabel(raw);
    return [{ label: "", value: statusLabel }];
  }
}

// 工具函数（对未知值 fallback 为原始英文值）
export function getCaseStatusLabel(status: string): string {
  return CASE_STATUS_MAP[status]?.label ?? status;
}

export function getCaseStatusColor(status: string): string {
  return CASE_STATUS_MAP[status]?.color ?? "bg-gray-100 text-gray-600";
}

export function getTaskStatusLabel(status: string): string {
  return TASK_STATUS_MAP[status]?.label ?? status;
}

export function getTaskStatusColor(status: string): string {
  return TASK_STATUS_MAP[status]?.color ?? "bg-gray-100 text-gray-600";
}

export function getAgentName(name: string): string {
  return AGENT_NAME_MAP[name] ?? name;
}

export function getRoleName(role: string): string {
  return ROLE_NAME_MAP[role] ?? role;
}

export function getApprovalTypeLabel(type: string): string {
  return APPROVAL_TYPE_MAP[type] ?? type;
}

export function getApprovalStatusLabel(status: string): string {
  return APPROVAL_STATUS_MAP[status]?.label ?? status;
}

export function getApprovalStatusColor(status: string): string {
  return APPROVAL_STATUS_MAP[status]?.color ?? "bg-gray-100 text-gray-800";
}

export function getEvidenceTypeLabel(type: string): string {
  return EVIDENCE_TYPE_MAP[type] ?? type;
}

// 规则名中文映射（用于兼容旧数据中证据 summary 的英文规则名）
const RULE_NAME_MAP: Record<string, string> = {
  return_rate_7d:        "近7日退货率",
  return_rate_14d:       "近14日退货率",
  return_rate_28d:       "近28日退货率",
  settlement_delay_days: "回款延迟天数",
  return_amplification:  "退货放大倍数",
  cash_gap:              "现金缺口",
  order_amount:          "订单金额",
  refund_amount:         "退款金额",
};

/** 格式化证据 summary：将英文规则名替换为中文，数值按类型格式化 */
export function formatEvidenceSummary(summary: string): string {
  if (!summary) return summary;

  // 匹配模式："触发规则: xxx，值=yyy" 或 "触发规则: xxx, 值=yyy"
  const match = summary.match(/^触发规则:\s*([^，,]+)[，,]\s*值=(.+)$/);
  if (!match) return summary;

  const ruleKey = match[1].trim();
  const rawValue = match[2].trim();

  // 如果规则名已经是中文（新数据），直接返回
  const ruleLabel = RULE_NAME_MAP[ruleKey] ?? ruleKey;

  // 格式化值
  let formattedValue = rawValue;
  if (rawValue !== "N/A") {
    const numVal = parseFloat(rawValue);
    if (!isNaN(numVal)) {
      if (ruleKey.includes("rate")) {
        formattedValue = `${(numVal * 100).toFixed(2)}%`;
      } else if (ruleKey.includes("amplification")) {
        formattedValue = `${numVal.toFixed(2)}x`;
      } else if (ruleKey.includes("amount") || ruleKey.includes("gap")) {
        formattedValue = `¥${numVal.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
      } else if (ruleKey.includes("delay") || ruleKey.includes("days")) {
        formattedValue = `${numVal}天`;
      }
    }
  }

  return `触发规则: ${ruleLabel}，值=${formattedValue}`;
}
