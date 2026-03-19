## ADDED Requirements

### Requirement: 5 种角色定义
系统 SHALL 支持 5 种角色：风险运营（risk_ops）、融资运营（finance_ops）、理赔运营（claim_ops）、合规复核（compliance）、管理员（admin）。

#### Scenario: 角色列举
- **WHEN** 查询系统支持的角色列表
- **THEN** 返回 risk_ops、finance_ops、claim_ops、compliance、admin 五种角色

### Requirement: 角色访问控制
系统 SHALL 根据角色限制可访问的功能：
- 风险运营：查看案件、触发重分析、审批异常退货复核、查看证据链与轨迹
- 融资运营：查看现金缺口建议、审批融资申请、修改建议后提交
- 理赔运营：查看理赔材料草稿、审批理赔任务、补充理赔说明
- 合规复核：查看全部审计、查看模型与规则命中、拒绝高风险建议，但不可直接改业务建议
- 管理员：管理模型策略、连接器、审批策略、评测集、全局观测面板

#### Scenario: 风险运营访问案件
- **WHEN** risk_ops 角色用户请求 GET /api/risk-cases
- **THEN** 返回该用户有权访问的案件列表

#### Scenario: 合规角色不可修改建议
- **WHEN** compliance 角色用户尝试 PUT /api/recommendations/{id}
- **THEN** 系统返回 403 Forbidden

#### Scenario: 普通运营不可改模型策略
- **WHEN** risk_ops 角色用户尝试 POST /api/model-policies
- **THEN** 系统返回 403 Forbidden

### Requirement: 请求级权限中间件
系统 SHALL 通过 FastAPI 中间件在每个 API 请求中校验角色权限。

#### Scenario: 未认证请求被拒绝
- **WHEN** 未携带认证信息的请求访问受保护 API
- **THEN** 返回 401 Unauthorized

#### Scenario: 角色权限不足被拒绝
- **WHEN** 已认证但角色权限不足的请求访问受限 API
- **THEN** 返回 403 Forbidden
