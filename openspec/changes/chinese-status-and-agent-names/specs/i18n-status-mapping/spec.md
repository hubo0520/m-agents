## ADDED Requirements

### Requirement: 案件状态中文展示
系统前端所有展示案件状态的位置 SHALL 显示中文标签而非英文枚举值。状态中文映射覆盖以下所有值：
- `NEW` → "新建"
- `TRIAGED` → "已分诊"
- `ANALYZING` → "分析中"
- `RECOMMENDING` → "建议生成中"
- `PENDING_APPROVAL` → "待审批"
- `BLOCKED_BY_GUARD` → "合规拦截"
- `APPROVED` → "已通过"
- `EXECUTING` → "执行中"
- `WAITING_CALLBACK` → "等待回调"
- `COMPLETED` → "已完成"
- `PAUSED` → "已暂停"
- `RESUMED` → "已恢复"
- `PENDING_REVIEW` → "待审核"
- `ANALYZED` → "已分析"
- `REJECTED` → "已驳回"
- `FAILED_RETRYABLE` → "失败可重试"
- `FAILED_FINAL` → "最终失败"

#### Scenario: 首页看板案件列表状态展示
- **WHEN** 用户在首页看板查看案件列表
- **THEN** 每个案件的状态列显示对应的中文标签（如 "待审批"），而非英文值 "PENDING_APPROVAL"

#### Scenario: 案件详情页状态展示
- **WHEN** 用户进入某个案件的详情页
- **THEN** 页面顶部的状态标签显示中文（如 "已通过"），而非英文值 "APPROVED"

#### Scenario: 工作流列表页状态展示
- **WHEN** 用户在工作流监控页查看运行列表
- **THEN** 每条工作流运行记录的状态显示中文标签

#### Scenario: 未知状态 fallback
- **WHEN** 后端返回了一个映射中不存在的新状态值（如 "CUSTOM_STATUS"）
- **THEN** 前端直接显示该英文原始值 "CUSTOM_STATUS"，不报错也不白屏

### Requirement: 任务状态中文展示
系统前端所有展示任务状态的位置 SHALL 显示中文标签。状态中文映射覆盖以下值：
- `DRAFT` → "草稿"
- `PENDING` → "待处理"
- `PENDING_REVIEW` → "待审核"
- `IN_PROGRESS` → "进行中"
- `EXECUTING` → "执行中"
- `APPROVED` → "已通过"
- `REJECTED` → "已驳回"
- `COMPLETED` → "已完成"
- `CLOSED` → "已关闭"

#### Scenario: 任务看板状态展示
- **WHEN** 用户在任务看板页查看任务列表
- **THEN** 每个任务的状态标签显示中文（如 "待审核"），而非英文值 "PENDING_REVIEW"

#### Scenario: 理赔/融资任务详情页状态展示
- **WHEN** 用户进入理赔或融资任务详情页
- **THEN** 任务的审批状态显示中文标签

### Requirement: Agent 中文名展示
系统前端所有展示 Agent 名称的位置 SHALL 显示中文名称而非英文标识符。Agent 中文名映射覆盖以下值：
- `load_case_context` → "案件加载"
- `triage_case` → "案件分诊"
- `compute_metrics` → "指标计算"
- `forecast_gap` → "现金流预测"
- `collect_evidence` → "证据收集"
- `diagnose_case` → "风险诊断"
- `generate_recommendations` → "动作建议"
- `run_guardrails` → "合规校验"
- `create_approval_tasks` → "审批创建"
- `finalize_summary` → "案件总结"
- `write_audit_log` → "审计记录"

#### Scenario: 工作流详情页 Agent 名称展示
- **WHEN** 用户进入某次工作流运行的详情页查看节点执行记录
- **THEN** 每个节点的 Agent 名称显示中文名（如 "风险诊断"），而非英文值 "diagnose_case"

#### Scenario: 设置页 Agent 名称展示
- **WHEN** 用户在设置页查看或管理 Agent Prompt 配置
- **THEN** Agent 名称显示中文名

#### Scenario: 未知 Agent 名称 fallback
- **WHEN** 后端返回了一个映射中不存在的新 Agent 名称
- **THEN** 前端直接显示该英文原始值，不报错也不白屏

### Requirement: 集中映射配置
所有状态中文映射和 Agent 中文名映射 MUST 集中维护在单个配置文件（`frontend/src/lib/constants.ts`）中。各页面 MUST 从该配置文件导入映射数据，不得在页面内部重复定义映射表。

#### Scenario: 新增状态维护
- **WHEN** 后端新增了一个案件状态枚举值
- **THEN** 只需在 `constants.ts` 一处添加映射，所有页面自动生效

#### Scenario: 修改中文标签
- **WHEN** 运营希望将某个状态的中文标签从 "待审批" 改为 "审批中"
- **THEN** 只需在 `constants.ts` 一处修改，所有页面自动生效
