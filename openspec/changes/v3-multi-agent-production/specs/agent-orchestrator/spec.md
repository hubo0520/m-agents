## MODIFIED Requirements

### Requirement: Agent 编排从单体重构为 LangGraph 多节点图
系统 SHALL 将现有单体 Orchestrator（`agents/orchestrator.py`）重构为 LangGraph StateGraph，保留原有分析/推荐/证据/守卫逻辑，但拆分为独立 Agent 节点。原有 `run_full_analysis()` 函数 SHALL 被替换为 graph.invoke() 调用。

#### Scenario: 通过 graph 执行案件分析
- **WHEN** 系统对案件触发分析
- **THEN** 通过 LangGraph graph.invoke() 执行，依次经过 load_case_context → triage_case → compute_metrics → forecast_gap → diagnose_case → collect_evidence → generate_recommendations → run_guardrails → finalize_summary 节点

#### Scenario: 保留旧 Orchestrator 作为 fallback
- **WHEN** LangGraph 编排引擎初始化失败
- **THEN** 系统可降级到旧 Orchestrator 的 run_full_analysis() 执行分析

### Requirement: 新增 5 个 specialist Agent
系统 SHALL 新增 TriageAgent、ComplianceGuardAgent、ExecutionAgent、SummaryAgent 作为独立文件，MonitorAgent 以规则函数形式实现（非 LLM）。

#### Scenario: TriageAgent 输出案件分类
- **WHEN** TriageAgent 接收案件上下文
- **THEN** 输出 case_type（cash_gap / suspected_fraud / business_loan / insurance_claim）和 priority（high / medium / low）

#### Scenario: ExecutionAgent 调用连接器
- **WHEN** ExecutionAgent 收到审批通过的动作
- **THEN** 调用对应的工具/连接器执行动作（创建融资草稿/理赔草稿/回款加速/复核任务）
