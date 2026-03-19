## ADDED Requirements

### Requirement: 审批状态流转
系统 SHALL 支持以下案件状态流转：NEW → ANALYZED → PENDING_REVIEW → APPROVED/REJECTED。每次状态变更 MUST 记录审计日志。

#### Scenario: 正常审批流程
- **WHEN** 案件经过分析后进入 PENDING_REVIEW 状态，运营人员点击"批准"
- **THEN** 案件状态变为 APPROVED，审计日志记录此次操作

#### Scenario: 驳回需填理由
- **WHEN** 运营人员驳回一条建议但未填写理由
- **THEN** 系统拒绝此操作，提示"驳回必须填写理由"

### Requirement: 审批决定类型
系统 SHALL 支持三种审批决定：批准（approve）、修改后批准（approve_with_changes）、驳回（reject）。

#### Scenario: 修改后批准
- **WHEN** 运营人员修改建议内容后选择"修改后批准"
- **THEN** 保存修改后的 final_action_json，原始 Agent 建议不可覆盖

### Requirement: 原始 Agent 输出不可覆盖
审批过程中 MUST NOT 覆盖原始 Agent 输出，只能新增版本。修改后的结果保存在 reviews 表的 final_action_json 中。

#### Scenario: 版本保留
- **WHEN** 运营人员修改了 Agent 建议后批准
- **THEN** recommendations 表中原始记录不变，reviews 表中保存最终版本

### Requirement: 融资和反欺诈动作强制备注
对融资类（经营贷建议）和反欺诈类（异常退货复核）动作，审批时 MUST 填写备注。

#### Scenario: 融资类强制备注
- **WHEN** 运营人员批准一条经营贷建议但未填写备注
- **THEN** 系统拒绝操作，提示"融资类动作必须填写备注"

### Requirement: 审计日志完整性
每次关键操作 SHALL 在 audit_logs 表生成记录，包含 entity_type、entity_id、actor、action、old_value、new_value、created_at。

#### Scenario: 审计日志生成
- **WHEN** 运营人员审批案件
- **THEN** audit_logs 表新增一条记录，old_value 包含审批前状态，new_value 包含审批后状态

#### Scenario: 审计记录不可删除
- **WHEN** 系统运行过程中
- **THEN** 审计日志 MUST NOT 提供删除接口

### Requirement: 审批抽屉 UI
审批 SHALL 通过抽屉（Drawer）组件实现，在案件详情页右侧滑出，展示 Agent 原始建议、审批选项和备注输入框。

#### Scenario: 审批抽屉打开
- **WHEN** 用户点击"审批"按钮
- **THEN** 右侧滑出审批抽屉，显示 Agent 建议和审批表单
