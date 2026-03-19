## ADDED Requirements

### Requirement: LangGraph 显式 Graph 定义
系统 SHALL 使用 LangGraph 构建显式 graph 编排引擎，通过 StateGraph 定义 Agent 节点和边的连接关系。graph 定义 SHALL 存储在 `backend/app/workflow/graph.py`。

#### Scenario: Graph 正常初始化
- **WHEN** 系统启动时加载 workflow 模块
- **THEN** LangGraph StateGraph 成功编译，包含至少 14 个节点（load_case_context、triage_case、compute_metrics、forecast_gap、diagnose_case、collect_evidence、generate_recommendations、run_guardrails、create_approval_tasks、wait_for_approval、execute_actions、wait_external_callback、finalize_summary、write_audit_log）

### Requirement: 条件分支路由
系统 SHALL 支持基于 Triage Agent 输出的条件分支，根据 case_type 和 priority 决定走哪条子图路径（退货激增→现金缺口、退货异常→疑似欺诈、缺口持续→经营贷、保险→理赔）。

#### Scenario: 高风险退货案件走现金缺口路径
- **WHEN** Triage Agent 输出 case_type="cash_gap" 且 priority="high"
- **THEN** graph 路由至 forecast_gap → diagnose_case → generate_recommendations 分支

#### Scenario: 疑似欺诈案件走复核路径
- **WHEN** Triage Agent 输出 case_type="suspected_fraud"
- **THEN** graph 路由至 collect_evidence → run_guardrails → create_approval_tasks(fraud_review) 分支

### Requirement: 至少 6 个 Agent 节点可独立运行
系统 SHALL 支持至少 6 个 specialist Agent 节点独立运行，每个节点具备独立的输入/输出 schema。

#### Scenario: 单个 Agent 节点独立执行
- **WHEN** 在测试环境调用 DiagnosisAgent.run(input_data)
- **THEN** Agent 返回符合 DiagnosisOutput schema 的结构化结果

### Requirement: 节点失败后重试或人工接管
系统 SHALL 支持 graph 节点失败时自动重试（最多 3 次），重试失败后进入人工接管队列。

#### Scenario: LLM 节点超时后自动重试
- **WHEN** diagnose_case 节点调用 LLM 超时
- **THEN** 系统自动重试最多 3 次，每次使用指数退避策略

#### Scenario: 重试全部失败后进入人工接管
- **WHEN** 节点 3 次重试全部失败
- **THEN** workflow 状态变为 FAILED_RETRYABLE，创建人工接管任务

### Requirement: 案件状态机
系统 SHALL 实现完整案件状态机：NEW → TRIAGED → ANALYZING → RECOMMENDING → PENDING_APPROVAL → EXECUTING → WAITING_CALLBACK → COMPLETED，并支持异常分支（NEEDS_MORE_DATA、BLOCKED_BY_GUARD、REJECTED、FAILED_RETRYABLE、FAILED_FINAL、PAUSED → RESUMED）。

#### Scenario: 正常案件全流程状态流转
- **WHEN** 一个新案件从 NEW 状态开始执行 workflow
- **THEN** 案件依次经过 TRIAGED → ANALYZING → RECOMMENDING → PENDING_APPROVAL → EXECUTING → COMPLETED 状态

#### Scenario: 被守卫阻断的案件
- **WHEN** run_guardrails 节点检测到违规输出
- **THEN** 案件状态变为 BLOCKED_BY_GUARD，workflow 暂停等待人工处理
