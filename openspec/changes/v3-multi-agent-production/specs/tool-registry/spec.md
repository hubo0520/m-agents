## ADDED Requirements

### Requirement: 统一工具注册
系统 SHALL 提供统一的工具注册中心，每个工具具备 tool_name、version、description、approval_policy（是否需要审批）。

#### Scenario: 注册新工具
- **WHEN** 管理员在工具中心注册一个新工具（如 submit_advance_settlement）
- **THEN** 工具记录包含 tool_name、version、approval_policy=REQUIRED

#### Scenario: 查询可用工具列表
- **WHEN** Agent 执行时查询可用工具
- **THEN** 返回当前活跃的工具列表，包含每个工具的 allowlist 信息

### Requirement: 工具调用日志
系统 SHALL 将每次工具调用记录到 `tool_invocations` 表，包含 workflow_run_id、tool_name、tool_version、input_json、output_json、approval_required、approval_status、status、idempotency_key、created_at。

#### Scenario: 工具调用成功记录
- **WHEN** Execution Agent 调用 query_credit_score 工具成功
- **THEN** 写入 tool_invocations 记录，status=SUCCESS

#### Scenario: 工具调用失败记录
- **WHEN** 工具调用超时或返回错误
- **THEN** 写入 tool_invocations 记录，status=FAILED，output_json 包含错误信息

### Requirement: 工具幂等键
系统 SHALL 为每次工具调用生成 idempotency_key，防止重复执行。

#### Scenario: 幂等键防重
- **WHEN** 系统对同一 workflow_run + tool_name + 相同参数 的调用已存在成功记录
- **THEN** 返回已有记录结果，不再重复调用

### Requirement: 审批前置拦截
系统 SHALL 在调用 approval_policy=REQUIRED 的工具前，先创建审批任务，审批通过后方可执行。

#### Scenario: 写操作工具需审批
- **WHEN** Execution Agent 尝试调用 submit_advance_settlement 工具（approval_policy=REQUIRED）
- **THEN** 系统创建审批任务，workflow 暂停等待审批
