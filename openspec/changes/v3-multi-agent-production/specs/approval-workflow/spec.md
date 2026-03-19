## MODIFIED Requirements

### Requirement: 审批从案件级扩展为 Workflow 级审批门禁
系统 SHALL 将现有案件级别的简单审批（reviews 表）扩展为统一审批中心，支持 workflow 级别的审批门禁。现有 reviews 表和 `/api/risk-cases/{case_id}/review` 接口 SHALL 保留（向后兼容），新增 approval_tasks 表用于 workflow 级审批。

#### Scenario: 旧审批接口继续可用
- **WHEN** 前端调用 POST /api/risk-cases/{case_id}/review 提交案件审批
- **THEN** 系统正常处理，reviews 表写入审批记录（向后兼容）

#### Scenario: Workflow 审批门禁
- **WHEN** workflow 执行到 create_approval_tasks 节点
- **THEN** 系统在 approval_tasks 表创建审批记录，workflow 暂停在 wait_for_approval 节点

#### Scenario: 审批通过后自动恢复 workflow
- **WHEN** 审批人员通过 POST /api/approvals/{id}/approve 批准
- **THEN** approval_task.status 变为 APPROVED，关联 workflow 自动从 wait_for_approval 恢复到 execute_actions
