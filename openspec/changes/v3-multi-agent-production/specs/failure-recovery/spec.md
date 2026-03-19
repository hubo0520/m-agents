## ADDED Requirements

### Requirement: 三级降级策略
系统 SHALL 实现三级降级策略：L1 自动重试（最多 3 次，指数退避）→ L2 LLM 节点降级到规则引擎 → L3 创建人工处理任务。

#### Scenario: L1 自动重试成功
- **WHEN** LLM 节点首次调用超时
- **THEN** 系统在 2 秒后自动重试，第二次成功

#### Scenario: L2 降级到规则引擎
- **WHEN** LLM 节点 3 次重试全部失败
- **THEN** 系统切换到 engine/rules.py 中的规则引擎生成替代建议，workflow 继续执行

#### Scenario: L3 人工接管
- **WHEN** 规则引擎也无法产出有效建议
- **THEN** 系统创建人工处理任务，workflow 进入 PAUSED 状态等待人工干预

### Requirement: 外部工具失败处理
外部工具调用失败时，系统 SHALL 记录失败详情并进入人工处理流程。

#### Scenario: 外部连接器调用失败
- **WHEN** Execution Agent 调用外部回款加速接口返回 5xx 错误
- **THEN** tool_invocations 记录 status=FAILED，workflow 进入 FAILED_RETRYABLE，管理员可选择重试或人工处理

### Requirement: 失败记录写入审计
所有失败 SHALL 同时写入 audit_logs 和 workflow_runs，包含失败原因、失败节点、降级路径。

#### Scenario: 查看失败历史
- **WHEN** 管理员查看某个 workflow 的失败历史
- **THEN** 可看到每次失败的时间、节点、原因、采取的降级策略

### Requirement: 可重试任务手动重试
系统 SHALL 支持对 FAILED_RETRYABLE 状态的 workflow 手动触发重试。

#### Scenario: 手动重试失败的 workflow
- **WHEN** 管理员在工作流运行中心选择一个 FAILED_RETRYABLE 的 workflow，点击"重试"
- **THEN** 系统从失败节点重新开始执行，使用最新的 checkpoint 状态
