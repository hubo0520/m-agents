## ADDED Requirements

### Requirement: Prompt 版本管理
系统 SHALL 维护 `prompt_versions` 表，记录每个 Agent 的 prompt 历史版本（agent_name、version、content、status、created_at）。

#### Scenario: 创建新 prompt 版本
- **WHEN** 管理员提交新的 DiagnosisAgent prompt 内容
- **THEN** 创建 prompt_versions 记录，version 自增，status=DRAFT

#### Scenario: 激活 prompt 版本
- **WHEN** 管理员将某个 prompt 版本设为 ACTIVE
- **THEN** 该 Agent 后续执行使用新版本 prompt，旧版本 status 变为 ARCHIVED

### Requirement: Schema 版本管理
系统 SHALL 维护 `schema_versions` 表，记录每个 Agent 的输出 schema 历史版本（agent_name、version、json_schema、created_at）。

#### Scenario: 创建新 schema 版本
- **WHEN** 管理员提交新的 Agent 输出 schema
- **THEN** 创建 schema_versions 记录

### Requirement: Agent Run 版本绑定
每次 agent_run MUST 绑定使用的 model_name、prompt_version、schema_version。

#### Scenario: 版本追溯
- **WHEN** 查看某个案件的 agent_run 详情
- **THEN** 可看到该次运行使用的 prompt 版本号、schema 版本号、模型名称

### Requirement: 版本回滚
系统 SHALL 支持将 Agent 的 prompt 和 schema 回滚到历史版本。

#### Scenario: 回滚到旧版本
- **WHEN** 管理员选择 DiagnosisAgent prompt v2 并执行"回滚"
- **THEN** v2 变为 ACTIVE，当前活跃版本变为 ARCHIVED

### Requirement: 灰度开关
系统 SHALL 支持 prompt/schema 新版本的灰度发布，可按比例分配流量到新版本。

#### Scenario: 50% 灰度
- **WHEN** 管理员将新 prompt 设为 50% 灰度
- **THEN** 约 50% 的新 workflow 使用新版本 prompt，50% 使用旧版本
