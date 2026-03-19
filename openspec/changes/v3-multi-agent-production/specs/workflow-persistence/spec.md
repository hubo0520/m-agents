## ADDED Requirements

### Requirement: Workflow Run 落库
系统 SHALL 将每个 workflow run 的状态信息持久化到 `workflow_runs` 表，包含 id、case_id、graph_version、status、current_node、started_at、updated_at、paused_at、resumed_at、ended_at。

#### Scenario: 新 workflow run 创建
- **WHEN** 系统为案件启动新的 workflow
- **THEN** 创建 workflow_runs 记录，status=NEW，current_node=load_case_context

#### Scenario: 节点执行时更新当前状态
- **WHEN** workflow 进入 diagnose_case 节点
- **THEN** workflow_runs.current_node 更新为 "diagnose_case"，updated_at 更新为当前时间

### Requirement: Checkpoint 持久化
系统 SHALL 使用 langgraph-checkpoint-sqlite 将 LangGraph checkpoint 持久化到 SQLite，支持故障恢复。

#### Scenario: 节点完成后写入 checkpoint
- **WHEN** 每个 graph 节点执行完成
- **THEN** checkpoint 自动写入 checkpoints 表

#### Scenario: 服务重启后从 checkpoint 恢复
- **WHEN** 服务进程重启，且有未完成的 workflow run
- **THEN** 系统从最近的 checkpoint 恢复 graph 状态，从中断节点继续执行

### Requirement: Agent Run 记录
系统 SHALL 将每个 Agent 节点的执行记录写入 `agent_runs` 表，包含 workflow_run_id、agent_name、model_name、prompt_version、schema_version、input_json、output_json、status、latency_ms。

#### Scenario: Agent 节点执行完成后记录
- **WHEN** DiagnosisAgent 节点执行完成
- **THEN** 写入 agent_runs 记录，包含输入输出 JSON、使用的模型版本、耗时

### Requirement: 审批后从中断点继续
系统 SHALL 支持 wait_for_approval 节点暂停 workflow，审批完成后从暂停点恢复执行。

#### Scenario: 审批通过后恢复 workflow
- **WHEN** 审批人员点击"批准"按钮
- **THEN** 关联的 workflow run 从 PAUSED 恢复为 EXECUTING，从 execute_actions 节点继续

#### Scenario: 审批驳回后终止 workflow
- **WHEN** 审批人员点击"驳回"按钮
- **THEN** workflow run 状态变为 REJECTED，记录驳回原因

### Requirement: 节点结果不可丢失
系统 SHALL 保证任何已完成节点的 agent_run 输出不可被覆盖或删除，仅可追加新版本。

#### Scenario: 重新分析不覆盖历史
- **WHEN** 对同一案件触发重新分析
- **THEN** 创建新的 workflow_run 记录，旧记录和 agent_runs 保持不变
