## ADDED Requirements

### Requirement: 案件列表 API
系统 SHALL 提供 GET /api/risk-cases 端点，支持 risk_level、status、merchant_name、page、page_size 查询参数。

#### Scenario: 获取案件列表
- **WHEN** 调用 GET /api/risk-cases?risk_level=high&page=1&page_size=10
- **THEN** 返回 high 风险等级的案件列表，分页信息正确

#### Scenario: 搜索商家名称
- **WHEN** 调用 GET /api/risk-cases?merchant_name=女装
- **THEN** 返回商家名称包含"女装"的案件

### Requirement: 案件详情 API
系统 SHALL 提供 GET /api/risk-cases/{case_id} 端点，返回完整案件信息包括商家信息、核心指标、趋势图数据、Agent 摘要、建议列表、证据列表、审计记录。

#### Scenario: 获取案件详情
- **WHEN** 调用 GET /api/risk-cases/1
- **THEN** 返回案件完整信息，响应时间 P95 < 1s

### Requirement: 重新分析 API
系统 SHALL 提供 POST /api/risk-cases/{case_id}/analyze 端点，触发 Agent 重新分析。

#### Scenario: 触发重新分析
- **WHEN** 调用 POST /api/risk-cases/1/analyze
- **THEN** 重新运行分析流程，更新案件的 Agent 输出，返回更新后的案件信息

### Requirement: 获取证据 API
系统 SHALL 提供 GET /api/risk-cases/{case_id}/evidence 端点，返回案件关联的所有证据。

#### Scenario: 获取证据列表
- **WHEN** 调用 GET /api/risk-cases/1/evidence
- **THEN** 返回案件关联的证据列表，每条包含 evidence_type、summary、source_table、source_id

### Requirement: 审批 API
系统 SHALL 提供 POST /api/risk-cases/{case_id}/review 端点，接受 decision、comment、final_actions 请求体。

#### Scenario: 审批案件
- **WHEN** 调用 POST /api/risk-cases/1/review，body 为 {"decision": "approve", "comment": "同意"}
- **THEN** 案件状态更新为 APPROVED，审计日志生成

#### Scenario: 驳回无理由
- **WHEN** 调用 POST /api/risk-cases/1/review，body 为 {"decision": "reject", "comment": ""}
- **THEN** 返回 400 错误，提示"驳回必须填写理由"

### Requirement: 导出 API
系统 SHALL 提供 GET /api/risk-cases/{case_id}/export?format=markdown|json 端点。

#### Scenario: 导出 Markdown
- **WHEN** 调用 GET /api/risk-cases/1/export?format=markdown
- **THEN** 返回 Markdown 格式的案件摘要

### Requirement: 看板指标 API
系统 SHALL 提供 GET /api/dashboard/stats 端点，返回看板顶部指标卡数据。

#### Scenario: 获取看板指标
- **WHEN** 调用 GET /api/dashboard/stats
- **THEN** 返回 merchant_count、new_high_risk_count、total_predicted_gap、avg_settlement_delay

### Requirement: CORS 支持
后端 SHALL 配置 CORSMiddleware，允许前端开发服务器（localhost:3000）跨域访问。

#### Scenario: 跨域请求
- **WHEN** 前端从 localhost:3000 调用后端 localhost:8000 的 API
- **THEN** 请求正常响应，无 CORS 错误
