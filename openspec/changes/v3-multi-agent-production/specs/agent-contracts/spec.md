## ADDED Requirements

### Requirement: 通用 Agent 输入契约
所有 Agent SHALL 接受统一的输入结构：case_id、merchant_id、state_version、trigger_type、context_refs（引用的上下文版本列表）、policy_version。

#### Scenario: Agent 接收标准输入
- **WHEN** graph 节点调用 DiagnosisAgent
- **THEN** 传入的输入数据符合 AgentInput Pydantic schema，包含 case_id、merchant_id 等字段

### Requirement: 各 Agent 独立输出 Schema
每个 Agent SHALL 定义独立的 Pydantic 输出 schema，输出 MUST 通过 OpenAI Structured Outputs 生成。

#### Scenario: Triage Agent 输出
- **WHEN** TriageAgent 完成执行
- **THEN** 输出符合 TriageOutput schema（case_type、priority、recommended_path）

#### Scenario: Diagnosis Agent 输出
- **WHEN** DiagnosisAgent 完成执行
- **THEN** 输出符合 DiagnosisOutput schema（root_causes、business_summary、key_factors）

#### Scenario: Recommendation Agent 输出
- **WHEN** RecommendationAgent 完成执行
- **THEN** 输出符合 RecommendationOutput schema（risk_level、recommendations 列表，每条包含 action_type、title、why、expected_benefit、confidence、requires_manual_review、evidence_ids）

#### Scenario: Guard Agent 输出
- **WHEN** ComplianceGuardAgent 完成执行
- **THEN** 输出符合 GuardOutput schema（passed、reason_codes、blocked_actions、next_state）

### Requirement: Agent 间通信使用 Pydantic
所有 Agent 间的数据传递 SHALL 通过 Pydantic 模型进行序列化/反序列化，不允许使用裸 dict。

#### Scenario: graph state 包含 typed 数据
- **WHEN** graph 在节点间传递 state
- **THEN** state 中所有 Agent 输出字段均为对应 Pydantic 模型的实例

### Requirement: Schema 校验失败阻断
系统 SHALL 在 Agent 输出不符合 schema 时阻断后续流程。

#### Scenario: 输出 schema 校验失败
- **WHEN** Agent 输出的 JSON 不符合其定义的 Pydantic schema
- **THEN** 系统阻断该节点，标记为 FAILED，记录 schema 校验错误信息
