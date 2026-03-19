## Context

当前系统的前端展示层直接使用后端 API 返回的英文枚举值作为用户可见的状态文本和 Agent 名称。涉及以下两类问题：

1. **案件/工作流/任务状态**：如 `PENDING_APPROVAL`、`BLOCKED_BY_GUARD`、`FAILED_RETRYABLE` 等英文状态直接渲染在页面上，运营人员需要自行理解含义。
2. **Agent 节点名称**：如 `load_case_context`、`diagnose_case`、`run_guardrails` 等下划线分隔的英文标识符直接展示在工作流详情和设置页面中。

当前的 `StatusBadge` 组件（在 `page.tsx` 和 `cases/[id]/page.tsx` 中各有一份独立实现）仅做了颜色映射，文本部分直接输出 `{status}` 原始值。`tasks/page.tsx` 中部分任务状态已有中文标签（如 "待审核"、"已通过"），但未统一。

## Goals / Non-Goals

**Goals:**
- 所有面向用户的状态文本统一以中文展示
- 所有面向用户的 Agent 名称统一以中文展示
- 建立一个集中维护的映射配置，避免在各页面中分散硬编码
- 对未知状态值或未知 Agent 名称提供 fallback（显示原始英文值），保证不会因新增状态导致页面白屏

**Non-Goals:**
- 不做完整的 i18n 国际化框架集成（不引入 i18next 等库）
- 不修改后端 API 返回的状态枚举值（保持英文作为机器可读标准）
- 不修改数据库中的状态存储格式

## Decisions

### 1. 新增集中映射配置文件

**决策**：在 `frontend/src/lib/` 下新增 `constants.ts` 文件，集中维护状态中文映射和 Agent 中文名映射。

**理由**：当前颜色映射分散在 `page.tsx`、`cases/[id]/page.tsx`、`workflows/page.tsx`、`tasks/page.tsx` 等多个文件中，每个文件各自维护一份。集中管理后，新增状态或修改译名只需改一个文件。

**结构设计**：

```typescript
// frontend/src/lib/constants.ts

// 案件状态映射（含颜色 + 中文标签）
export const CASE_STATUS_MAP: Record<string, { label: string; color: string }> = {
  NEW:               { label: "新建",     color: "bg-blue-100 text-blue-700" },
  TRIAGED:           { label: "已分诊",   color: "bg-indigo-100 text-indigo-800" },
  ANALYZING:         { label: "分析中",   color: "bg-purple-100 text-purple-700" },
  RECOMMENDING:      { label: "建议生成中", color: "bg-violet-100 text-violet-800" },
  PENDING_APPROVAL:  { label: "待审批",   color: "bg-yellow-100 text-yellow-800" },
  BLOCKED_BY_GUARD:  { label: "合规拦截", color: "bg-orange-100 text-orange-800" },
  APPROVED:          { label: "已通过",   color: "bg-green-100 text-green-700" },
  EXECUTING:         { label: "执行中",   color: "bg-cyan-100 text-cyan-800" },
  WAITING_CALLBACK:  { label: "等待回调", color: "bg-teal-100 text-teal-800" },
  COMPLETED:         { label: "已完成",   color: "bg-green-100 text-green-800" },
  PAUSED:            { label: "已暂停",   color: "bg-orange-100 text-orange-800" },
  RESUMED:           { label: "已恢复",   color: "bg-blue-100 text-blue-800" },
  PENDING_REVIEW:    { label: "待审核",   color: "bg-orange-100 text-orange-700" },
  ANALYZED:          { label: "已分析",   color: "bg-purple-100 text-purple-700" },
  REJECTED:          { label: "已驳回",   color: "bg-red-100 text-red-700" },
  FAILED_RETRYABLE:  { label: "失败可重试", color: "bg-red-100 text-red-700" },
  FAILED_FINAL:      { label: "最终失败", color: "bg-red-200 text-red-900" },
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
  load_case_context:       "案件加载",
  triage_case:             "案件分诊",
  compute_metrics:         "指标计算",
  forecast_gap:            "现金流预测",
  collect_evidence:        "证据收集",
  diagnose_case:           "风险诊断",
  generate_recommendations:"动作建议",
  run_guardrails:          "合规校验",
  create_approval_tasks:   "审批创建",
  finalize_summary:        "案件总结",
  write_audit_log:         "审计记录",
};

// 工具函数
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
```

### 2. 统一 StatusBadge 为共享组件引用

**决策**：各页面的 `StatusBadge` 组件改为从 `constants.ts` 的映射中取 label 和 color，不再各自维护颜色表。

**理由**：当前首页和案件详情页各有一份独立的 `StatusBadge` 实现，颜色定义不完全一致。统一映射源后可保证一致性。

### 3. Agent 名称展示策略

**决策**：在 Agent 中文名后面不附带英文原名。仅展示中文名，因为英文标识符对运营人员无价值。

## Risks / Trade-offs

- **[风险] 新增状态未加入映射** → fallback 机制会直接显示英文原值，不会白屏。新增状态时需同步更新 `constants.ts`。
- **[风险] 部分页面遗漏改造** → 通过任务清单逐页排查，确保 8 个页面全部覆盖。
- **[权衡] 不引入 i18n 框架** → 本次需求仅涉及中文展示，引入 i18n 框架（如 i18next）收益不大但增加复杂度。如未来有多语言需求可再重构。
