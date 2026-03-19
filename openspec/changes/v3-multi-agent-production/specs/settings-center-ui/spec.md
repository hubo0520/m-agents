## ADDED Requirements

### Requirement: Prompt 版本管理界面
系统 SHALL 提供 `/settings` 页面中的 Prompt 版本管理 Tab，展示各 Agent 的 prompt 版本列表，支持创建、激活、归档操作。

#### Scenario: 查看 prompt 版本列表
- **WHEN** 用户访问 `/settings` 并选择 "Prompt 版本" Tab
- **THEN** 展示每个 Agent 的 prompt 版本列表，包含版本号、状态（DRAFT/ACTIVE/ARCHIVED）、创建时间

#### Scenario: 创建新 prompt 版本
- **WHEN** 用户点击"创建版本"，输入 prompt 内容并提交
- **THEN** 创建新的 prompt_version 记录，status=DRAFT

### Requirement: Schema 版本管理界面
系统 SHALL 在设置中心提供 Schema 版本管理 Tab。

#### Scenario: 查看 schema 版本
- **WHEN** 用户选择 "Schema 版本" Tab
- **THEN** 展示每个 Agent 的 schema 版本列表和 JSON Schema 内容预览

### Requirement: 模型策略管理界面
系统 SHALL 在设置中心提供模型策略管理 Tab，配置每个 Agent 使用的模型名称和参数。

#### Scenario: 修改 Agent 模型
- **WHEN** 管理员将 DiagnosisAgent 的模型从 gpt-4o 改为 gpt-4o-mini
- **THEN** 保存配置，后续该 Agent 使用新模型

### Requirement: 工具配置管理界面
系统 SHALL 在设置中心提供工具配置管理 Tab，管理 tool allowlist 和 approval_policy。

#### Scenario: 查看工具配置
- **WHEN** 管理员访问"工具配置" Tab
- **THEN** 展示所有注册工具及其 approval_policy 设置

### Requirement: 审批规则管理界面
系统 SHALL 在设置中心提供审批规则管理 Tab，配置哪些动作需要审批、SLA 时间等。

#### Scenario: 修改审批 SLA
- **WHEN** 管理员将 business_loan 审批的 SLA 从 24h 改为 12h
- **THEN** 后续生成的该类审批任务 due_at 按 12h 计算
