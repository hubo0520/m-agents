## 1. 新增集中映射配置

- [x] 1.1 创建 `frontend/src/lib/constants.ts`，定义 `CASE_STATUS_MAP`（案件状态 → 中文标签 + 颜色）、`TASK_STATUS_MAP`（任务状态 → 中文标签 + 颜色）、`AGENT_NAME_MAP`（Agent 英文标识 → 中文名）三个映射表
- [x] 1.2 在 `constants.ts` 中导出工具函数：`getCaseStatusLabel`、`getCaseStatusColor`、`getTaskStatusLabel`、`getTaskStatusColor`、`getAgentName`，对未知值返回原始英文值作为 fallback

## 2. 案件状态中文化

- [x] 2.1 改造 `frontend/src/app/page.tsx`（首页看板）中的 `StatusBadge` 组件，从 `constants.ts` 导入映射，展示中文标签
- [x] 2.2 改造 `frontend/src/app/cases/[id]/page.tsx`（案件详情页）中的 `StatusBadge` 组件，从 `constants.ts` 导入映射，展示中文标签
- [x] 2.3 改造 `frontend/src/app/workflows/page.tsx`（工作流列表页），将 `STATUS_COLORS` 替换为从 `constants.ts` 导入的 `CASE_STATUS_MAP`，状态文本展示中文标签
- [x] 2.4 改造 `frontend/src/app/workflows/page.tsx` 中筛选下拉框的 option 文本为中文

## 3. 任务状态中文化

- [x] 3.1 改造 `frontend/src/app/tasks/page.tsx`（任务看板页），将本地 statusConfig 替换为从 `constants.ts` 导入的 `TASK_STATUS_MAP`，展示中文标签
- [x] 3.2 改造 `frontend/src/app/tasks/claims/[id]/page.tsx`（理赔任务详情页），审批状态展示中文标签
- [x] 3.3 改造 `frontend/src/app/tasks/financing/[id]/page.tsx`（融资任务详情页），审批状态展示中文标签

## 4. Agent 名称中文化

- [x] 4.1 改造 `frontend/src/app/workflows/[id]/page.tsx`（工作流详情页），Agent 名称展示中文名
- [x] 4.2 改造 `frontend/src/app/settings/page.tsx`（设置页），Agent 名称展示中文名（下拉选项和表格列）

## 5. 验证

- [x] 5.1 编译验证：执行 `npx tsc --noEmit` 确认无类型错误
- [ ] 5.2 页面验证：依次访问首页看板、案件详情、工作流列表、工作流详情、任务看板、理赔详情、融资详情、设置页，确认所有状态和 Agent 名称均显示中文
