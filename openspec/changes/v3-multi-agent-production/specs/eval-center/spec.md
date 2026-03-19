## ADDED Requirements

### Requirement: 创建评测数据集
系统 SHALL 支持创建离线评测数据集（eval_datasets），包含 name、description、test_cases（JSON 数组，每条包含 input 和 expected_output）。

#### Scenario: 创建新数据集
- **WHEN** 管理员上传一组测试案例（10 条案件输入 + 期望的建议输出）
- **THEN** 创建 eval_datasets 记录，test_cases 包含 10 条测试数据

### Requirement: 运行评测
系统 SHALL 支持对指定版本（prompt_version + schema_version + model_name）运行评测。

#### Scenario: 执行离线评测
- **WHEN** 管理员选择评测数据集和目标版本，点击"运行评测"
- **THEN** 系统逐条执行测试案例，生成 eval_runs 记录和逐条 eval_results

### Requirement: 评测指标输出
系统 SHALL 输出以下评测指标：采纳率（建议与期望匹配率）、回退率（需人工修改率）、证据覆盖率（建议带 evidence_ids 比例）、schema 合格率（输出符合 schema 比例）。

#### Scenario: 查看评测结果
- **WHEN** 评测完成后查看结果
- **THEN** 展示 adoption_rate、rejection_rate、evidence_coverage_rate、schema_pass_rate 四项指标

### Requirement: 线上抽样评测
系统 SHALL 支持从线上 agent_runs 中随机抽样进行质量复核。

#### Scenario: 抽样复核
- **WHEN** 管理员设置"每日抽样 10 条 DiagnosisAgent 输出"
- **THEN** 系统自动从当日 agent_runs 中随机选取 10 条，生成待复核清单

### Requirement: 幻觉率监控
系统 SHALL 追踪 Agent 输出中的幻觉率（输出内容无法被证据支持的比例）。

#### Scenario: 幻觉检测
- **WHEN** 评测系统对 Agent 输出进行幻觉检查
- **THEN** 标记每条输出是否存在幻觉（evidence_ids 为空或不匹配），计算整体幻觉率
