## ADDED Requirements

### Requirement: 自动生成人工复核任务
当风险案件的建议中包含需要人工复核的行动（如 `anomaly_review`），或者 Agent 输出中 `manual_review_required` 为 true，系统 SHALL 自动生成人工复核任务并分配给指定运营人员。

#### Scenario: 异常退货触发复核任务
- **WHEN** 风险案件分析结果包含 action_type 为 `anomaly_review` 的建议
- **THEN** 系统自动创建一条复核任务记录，状态为 `PENDING`，包含 merchant_id、task_type（如 return_fraud）、review_reason、evidence_ids、assigned_to

#### Scenario: 手动触发复核任务生成
- **WHEN** 运营人员调用 `POST /api/risk-cases/{case_id}/generate-manual-review` 并传入 merchant_id、task_type 和 evidence_ids
- **THEN** 系统生成复核任务并返回 review_id

#### Scenario: 高风险案件强制生成复核任务
- **WHEN** 风险案件的 risk_level 为 `high` 且 Agent 输出中 manual_review_required 为 true
- **THEN** 系统 MUST 生成至少一条复核任务，即使没有 anomaly_review 类型的建议

### Requirement: 人工复核任务数据模型
系统 SHALL 在数据库中维护 `manual_reviews` 表，包含以下字段：id、merchant_id、case_id、recommendation_id、task_type、review_reason、evidence_ids_json、assigned_to、status、review_result、reviewer_comment、created_at、updated_at、completed_at。

#### Scenario: 复核任务包含证据引用
- **WHEN** 系统生成复核任务
- **THEN** evidence_ids_json 字段 MUST 包含来自案件证据表的关联证据 ID 列表

#### Scenario: 复核任务自动分配
- **WHEN** 系统生成复核任务时未指定 assigned_to
- **THEN** assigned_to 字段默认为 "unassigned"，运营人员可在任务管理页领取

### Requirement: 复核任务状态流转
复核任务 MUST 遵循状态机：`PENDING → IN_PROGRESS → COMPLETED → CLOSED`。

#### Scenario: 领取任务
- **WHEN** 运营人员领取一条 PENDING 状态的复核任务
- **THEN** 任务状态变为 IN_PROGRESS，assigned_to 更新为该运营人员 ID

#### Scenario: 完成复核
- **WHEN** 运营人员提交复核结果（review_result + reviewer_comment）
- **THEN** 任务状态变为 COMPLETED，completed_at 记录完成时间

#### Scenario: 关闭任务
- **WHEN** 管理员关闭一条复核任务
- **THEN** 任务状态变为 CLOSED，记录关闭原因
