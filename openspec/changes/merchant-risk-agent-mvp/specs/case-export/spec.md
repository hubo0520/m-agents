## ADDED Requirements

### Requirement: 导出案件摘要
系统 SHALL 支持将案件完整信息导出，包含：商家信息、风险摘要、现金缺口、建议动作、证据清单、审批记录。

#### Scenario: Markdown 格式导出
- **WHEN** 用户点击导出并选择 Markdown 格式
- **THEN** 下载一个 .md 文件，包含案件的所有摘要信息

#### Scenario: JSON 格式导出
- **WHEN** 用户点击导出并选择 JSON 格式
- **THEN** 下载一个 .json 文件，结构化包含案件所有字段

### Requirement: 导出内容完整性
导出文件 MUST 包含以下完整内容：
- 商家概况（名称、行业、等级）
- 风险结论（风险等级、摘要、根因）
- 14 日缺口预测数据
- 动作建议列表
- 证据列表
- 审批记录

#### Scenario: 导出内容校验
- **WHEN** 导出一个已审批的案件
- **THEN** 导出文件包含审批决定、审批人、审批意见

### Requirement: 导出 API 端点
系统 SHALL 提供 GET /api/risk-cases/{case_id}/export?format=markdown|json 端点。

#### Scenario: API 调用导出
- **WHEN** 调用 GET /api/risk-cases/RC-0001/export?format=markdown
- **THEN** 返回 Markdown 格式的案件摘要内容
