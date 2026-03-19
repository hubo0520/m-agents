## ADDED Requirements

### Requirement: 自动生成理赔申请草稿
当风险案件的建议中包含理赔类行动（如 `insurance_claim`），系统 SHALL 自动生成理赔申请草稿，包含商家信息、退货原因、退款金额、物流证据、保险保单信息。

#### Scenario: 异常退货触发理赔申请
- **WHEN** 风险案件分析结果包含 action_type 为 `insurance_claim` 的建议，且商家存在有效保险保单
- **THEN** 系统自动创建一条理赔申请记录，状态为 `DRAFT`，包含 merchant_id、claim_amount、claim_reason、evidence_snapshot_json、policy_id、source_case_id

#### Scenario: 商家无有效保单
- **WHEN** 风险案件分析结果包含 action_type 为 `insurance_claim` 的建议，但商家不存在有效保险保单
- **THEN** 系统不生成理赔申请，并在审计日志中记录"无有效保单"

#### Scenario: 手动触发理赔申请生成
- **WHEN** 运营人员调用 `POST /api/risk-cases/{case_id}/generate-claim-application` 并传入 merchant_id、claim_amount 和 claim_reason
- **THEN** 系统生成理赔申请草稿并返回 claim_id

### Requirement: 理赔申请数据模型
系统 SHALL 在数据库中维护 `claims` 表，包含以下字段：id、merchant_id、case_id、recommendation_id、policy_id、claim_amount、claim_reason、evidence_snapshot_json、return_details_json、claim_status、reviewer_comment、created_at、updated_at。

#### Scenario: 理赔申请包含退货详情
- **WHEN** 系统生成理赔申请草稿
- **THEN** return_details_json 字段 MUST 包含关联的退货记录摘要（退货笔数、退货总金额、主要退货原因分布）

#### Scenario: 理赔申请包含证据快照
- **WHEN** 系统生成理赔申请草稿
- **THEN** evidence_snapshot_json 字段 MUST 包含案件中与退货相关的证据项列表

### Requirement: 理赔申请状态流转
理赔申请 MUST 遵循状态机：`DRAFT → PENDING_REVIEW → APPROVED → REJECTED`。

#### Scenario: 提交审核
- **WHEN** 运营人员提交理赔申请审核
- **THEN** 申请状态从 DRAFT 变为 PENDING_REVIEW

#### Scenario: 审核通过
- **WHEN** 风控运营审核通过理赔申请
- **THEN** 申请状态变为 APPROVED，记录审核人和审核意见

#### Scenario: 审核驳回
- **WHEN** 风控运营驳回理赔申请
- **THEN** 申请状态变为 REJECTED，reviewer_comment 记录驳回原因
