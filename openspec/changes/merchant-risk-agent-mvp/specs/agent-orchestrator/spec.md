## ADDED Requirements

### Requirement: Orchestrator 协调子 Agent 执行
系统 SHALL 提供 Orchestrator.analyze(case_id) 函数，按以下顺序协调子 Agent：
1. 调用 MetricsEngine 计算商家核心指标
2. 调用 EvidenceAgent 收集证据
3. 调用 AnalysisAgent 生成案件摘要
4. 调用 RecommendAgent 生成动作建议
5. 调用 GuardrailEngine 校验输出
6. 保存结果到数据库，更新案件状态为 ANALYZED

#### Scenario: 完整分析流程
- **WHEN** 对案件 RC-0001 调用 Orchestrator.analyze
- **THEN** 依次执行指标计算、证据收集、摘要生成、建议生成、守卫校验，最终保存结果

#### Scenario: 分析失败回退
- **WHEN** Agent 分析过程中发生异常
- **THEN** 系统回退到"结构化指标 + 规则建议"模式，案件状态不变为 ANALYZED

### Requirement: 分析 Agent 生成案件摘要
AnalysisAgent SHALL 读取案件上下文（指标 + 证据），生成包含以下字段的摘要：
- risk_level：风险等级
- case_summary：1 段运营可读的摘要文本
- root_causes：3 条以内核心成因，每条含 label、explanation、confidence、evidence_ids
- manual_review_required：是否需要人工复核

#### Scenario: 摘要生成
- **WHEN** 商家退货率放大倍数 2.0，回款延迟 3 天
- **THEN** 摘要包含"退货率异常上升"和"回款延迟"两个根因

#### Scenario: 数字引用结构化结果
- **WHEN** 摘要中提到"退货率 24%"
- **THEN** 该数字 MUST 来自 MetricsEngine 的计算结果，而非 LLM 编造

### Requirement: 推荐 Agent 生成动作建议
RecommendAgent SHALL 根据案件情况输出动作建议，每条建议包含 action_type、title、why、expected_benefit、confidence、evidence_ids、requires_manual_review 字段。

#### Scenario: 回款加速建议
- **WHEN** 预计 14 日缺口 > 0 且有待结算金额
- **THEN** 生成 action_type="advance_settlement" 的建议

#### Scenario: 经营贷建议资格检查
- **WHEN** 商家经营历史 < 60 天
- **THEN** MUST NOT 推荐经营贷

#### Scenario: 融资类建议强制人工复核
- **WHEN** 建议涉及经营贷
- **THEN** requires_manual_review MUST 为 true

### Requirement: 证据 Agent 收集证据
EvidenceAgent SHALL 收集支撑每条结论的证据，生成 evidence_id 映射。证据类型包括：订单、退货、物流轨迹、回款记录、规则命中、产品匹配结果。

#### Scenario: 证据覆盖
- **WHEN** Agent 分析完成
- **THEN** 每条建议至少挂 1 条证据，每条核心成因至少挂 2 条证据或 1 条规则命中

### Requirement: 守卫规则引擎校验
GuardrailEngine SHALL 对 Agent 输出进行以下校验：
- JSON Schema 格式校验
- 融资/反欺诈类建议必须 requires_manual_review=true
- 不允许出现"建议直接放款"或"建议拒赔"等禁止性结论
- 所有数字必须引用 evidence_id

#### Scenario: 拦截违规结论
- **WHEN** Agent 输出包含"建议直接放款"
- **THEN** 守卫引擎拦截该结论，标记为违规

#### Scenario: JSON Schema 校验失败
- **WHEN** Agent 输出缺少必要字段
- **THEN** 守卫引擎返回校验失败，附带缺失字段信息

### Requirement: Agent 输出 JSON 规范
Agent 最终输出 MUST 符合以下 JSON Schema，包含 case_id、risk_level、case_summary、root_causes、cash_gap_forecast、recommendations、manual_review_required 字段。

#### Scenario: 输出格式正确
- **WHEN** Orchestrator 完成分析
- **THEN** 输出 JSON 可通过 JSON Schema 校验

### Requirement: 第一阶段 Mock 实现
第一阶段所有子 Agent SHALL 使用基于规则的 mock 实现，不调用真实 LLM API。Mock 实现 SHALL 生成与 JSON Schema 一致的结构化输出。

#### Scenario: Mock 模式运行
- **WHEN** 运行 Agent 分析
- **THEN** 不发起任何外部 LLM API 调用，使用本地规则生成输出
