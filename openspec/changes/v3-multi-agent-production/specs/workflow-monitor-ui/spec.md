## ADDED Requirements

### Requirement: Workflow Run 列表页
系统 SHALL 提供 `/workflows` 页面展示所有 workflow_run 记录，支持按 status 和 case_id 筛选。

#### Scenario: 查看全部工作流
- **WHEN** 用户访问 `/workflows`
- **THEN** 展示 workflow_run 列表，每行包含 run_id、case_id、status、current_node、started_at、耗时

#### Scenario: 按状态筛选
- **WHEN** 用户选择筛选条件 status=FAILED_RETRYABLE
- **THEN** 列表仅显示状态为 FAILED_RETRYABLE 的 workflow

### Requirement: Workflow 节点详情
系统 SHALL 展示每个 workflow run 的节点执行详情，包含节点名称、耗时、状态、输入输出摘要。

#### Scenario: 查看节点耗时
- **WHEN** 用户点击某个 workflow run 查看详情
- **THEN** 展示该 run 的节点执行时间线，每个节点显示名称、开始/结束时间、耗时、状态

### Requirement: 失败原因展示
系统 SHALL 在工作流详情中展示失败节点的错误信息。

#### Scenario: 查看失败原因
- **WHEN** 用户查看一个 FAILED_RETRYABLE 的 workflow 详情
- **THEN** 高亮显示失败节点，展示错误信息、失败时间、降级策略

### Requirement: 恢复入口
系统 SHALL 在工作流详情页提供"重试"和"恢复"操作按钮。

#### Scenario: 点击重试按钮
- **WHEN** 用户在 FAILED_RETRYABLE 的 workflow 详情页点击"重试"
- **THEN** 系统调用 POST /api/workflows/{run_id}/retry，workflow 从失败节点重新执行

#### Scenario: 暂停的 workflow 恢复
- **WHEN** 用户在 PAUSED 的 workflow 详情页点击"恢复"
- **THEN** 系统调用 POST /api/workflows/{run_id}/resume，workflow 从暂停节点继续
