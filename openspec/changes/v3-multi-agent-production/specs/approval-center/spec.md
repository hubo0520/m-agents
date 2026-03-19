## ADDED Requirements

### Requirement: 统一审批队列
系统 SHALL 提供统一的审批任务队列，所有敏感动作（经营贷建议、回款加速申请、反欺诈复核结论、理赔草稿提交）MUST 进入审批队列后方可执行。

#### Scenario: 经营贷建议进入审批
- **WHEN** Recommendation Agent 生成 action_type="business_loan_draft" 的建议
- **THEN** 系统自动创建 approval_task，approval_type="business_loan"，status="PENDING"

#### Scenario: 未审批不得执行
- **WHEN** 尝试执行一个 approval_required=true 且 approval_status≠APPROVED 的动作
- **THEN** 系统阻断执行并返回错误

### Requirement: 审批操作
系统 SHALL 支持审批人员对审批任务执行三种操作：批准（approve）、驳回（reject）、修改后批准（revise_and_approve）。

#### Scenario: 审批人员批准任务
- **WHEN** 审批人员在审批详情页点击"批准"，输入审批意见
- **THEN** approval_task.status 变为 APPROVED，审批意见写入记录，关联 workflow 自动恢复

#### Scenario: 审批人员驳回任务
- **WHEN** 审批人员点击"驳回"，输入驳回理由
- **THEN** approval_task.status 变为 REJECTED，workflow 进入 REJECTED 状态

#### Scenario: 审批人员修改后批准
- **WHEN** 审批人员修改 payload_json 中的参数后点击"修改后批准"
- **THEN** approval_task.status 变为 APPROVED，payload_json 更新为修改后的内容，workflow 使用新参数继续执行

### Requirement: 批量审批
系统 SHALL 支持审批人员批量选择多个同类型待审批任务并一键批准或驳回。

#### Scenario: 批量批准 3 个回款加速审批
- **WHEN** 审批人员勾选 3 个 advance_settlement 类型的待审批任务，点击"批量批准"
- **THEN** 3 个 approval_task 全部变为 APPROVED，3 个关联 workflow 自动恢复

### Requirement: SLA 超时提醒
系统 SHALL 为每个审批任务设置 SLA 截止时间（due_at），超时后自动提醒。

#### Scenario: 审批超时提醒
- **WHEN** approval_task 的 due_at 时间已过且 status 仍为 PENDING
- **THEN** 系统标记该任务为"超时"状态，在审批列表中高亮显示

### Requirement: 审批记录含完整审计信息
系统 SHALL 确保每条审批记录包含 reviewer（审批人）、reviewed_at（审批时间）、comment（审批意见）、final_action_json（最终执行参数）。

#### Scenario: 查看已审批任务的审计信息
- **WHEN** 查看一个已批准的审批任务详情
- **THEN** 展示审批人、审批时间、审批意见、最终执行参数的完整信息
