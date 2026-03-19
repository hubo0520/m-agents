## Why

前端页面中案件状态（如 `PENDING_APPROVAL`、`ANALYZING`、`BLOCKED_BY_GUARD` 等）和 Agent 节点名称（如 `load_case_context`、`diagnose_case` 等）均以英文原文直接展示，对运营人员阅读不友好。需要将所有面向用户的状态文本和 Agent 名称统一映射为中文显示，提升可读性和用户体验。

## What Changes

- 新增前端统一的**状态中文映射**配置，覆盖所有案件状态、工作流状态和任务状态
- 新增前端统一的 **Agent 中文名映射**配置，覆盖所有工作流节点 Agent
- 改造多个页面的 `StatusBadge` 组件，从直接输出英文改为查表输出中文
- 改造工作流详情页和设置页中 `agent_name` 的展示，从直接输出英文改为查表输出中文
- 涉及页面：首页看板 (`page.tsx`)、案件详情 (`cases/[id]/page.tsx`)、工作流列表 (`workflows/page.tsx`)、工作流详情 (`workflows/[id]/page.tsx`)、任务看板 (`tasks/page.tsx`)、理赔详情 (`tasks/claims/[id]/page.tsx`)、融资详情 (`tasks/financing/[id]/page.tsx`)、设置页 (`settings/page.tsx`)

## Capabilities

### New Capabilities
- `i18n-status-mapping`: 前端统一的状态和 Agent 名称中文映射配置模块，包括状态中文标签、Agent 中文名，以及相关的查询函数

### Modified Capabilities

## Impact

- **前端**: 修改 8 个页面文件 + 新增 1 个映射配置文件
- **后端**: 无改动（英文状态值仍作为 API 和数据库的标准值，仅前端展示层做映射）
- **兼容性**: 无 breaking change，映射函数对未知状态值做 fallback 兜底（直接显示原始英文值）
