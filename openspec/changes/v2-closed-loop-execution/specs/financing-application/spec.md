## ADDED Requirements

### Requirement: 自动生成融资申请草稿
当风险案件的建议中包含融资类行动（如 `business_loan`、`repayment_acceleration`），且商家符合融资资格时，系统 SHALL 自动生成融资申请草稿，包含商家基本信息、资金需求金额、贷款用途、历史回款情况和还款计划。

#### Scenario: 现金缺口触发融资申请
- **WHEN** 风险案件分析结果包含 action_type 为 `business_loan` 的建议，且规则引擎判定商家符合融资资格
- **THEN** 系统自动创建一条融资申请记录，状态为 `DRAFT`，包含 merchant_id、amount_requested（等于预测现金缺口）、loan_purpose、repayment_plan_json、source_case_id、source_recommendation_id

#### Scenario: 商家不符合融资资格
- **WHEN** 风险案件分析结果包含 action_type 为 `business_loan` 的建议，但规则引擎判定商家不符合融资资格
- **THEN** 系统不生成融资申请，Recommendation 的 task_generated 保持 false，并在审计日志中记录"资格不通过"原因

#### Scenario: 手动触发融资申请生成
- **WHEN** 运营人员调用 `POST /api/risk-cases/{case_id}/generate-financing-application` 并传入 merchant_id 和 amount_requested
- **THEN** 系统生成融资申请草稿并返回 application_id，忽略自动资格判断

### Requirement: 融资申请数据模型
系统 SHALL 在数据库中维护 `financing_applications` 表，包含以下字段：id、merchant_id、case_id、recommendation_id、amount_requested、loan_purpose、repayment_plan_json、merchant_info_snapshot_json、historical_settlement_json、approval_status、reviewer_comment、created_at、updated_at。

#### Scenario: 融资申请包含完整商家快照
- **WHEN** 系统生成融资申请草稿
- **THEN** merchant_info_snapshot_json 字段 MUST 包含商家名称、行业、店铺等级、结算周期、总销售额、总退货额的快照数据

#### Scenario: 融资申请包含历史回款数据
- **WHEN** 系统生成融资申请草稿
- **THEN** historical_settlement_json 字段 MUST 包含商家近 90 天的回款记录摘要（总金额、平均周期、延迟率）

### Requirement: 融资申请状态流转
融资申请 MUST 遵循状态机：`DRAFT → PENDING_REVIEW → APPROVED → REJECTED`。

#### Scenario: 提交审核
- **WHEN** 运营人员在融资申请详情页点击"提交审核"
- **THEN** 申请状态从 DRAFT 变为 PENDING_REVIEW，并记录审计日志

#### Scenario: 审核通过
- **WHEN** 融资运营审核通过融资申请
- **THEN** 申请状态变为 APPROVED，并记录审核人和审核意见

#### Scenario: 审核驳回
- **WHEN** 融资运营驳回融资申请
- **THEN** 申请状态变为 REJECTED，reviewer_comment 记录驳回原因
