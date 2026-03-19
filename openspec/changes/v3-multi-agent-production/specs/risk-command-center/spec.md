## ADDED Requirements

### Requirement: 风险指挥台布局
系统 SHALL 将现有风险看板页面（`/`）升级为风险指挥台，新增以下模块：高优先级待审批事项、处理中案件、失败/待恢复工作流数量。

#### Scenario: 指挥台首页展示
- **WHEN** 用户访问首页 `/`
- **THEN** 页面展示：顶部指标卡（新增案件数、处理中案件数、待审批数、失败工作流数）、待审批事项快捷列表、案件趋势图、案件列表

### Requirement: 快捷审批入口
风险指挥台 SHALL 展示高优先级待审批事项的快捷入口，可直接跳转到审批详情页。

#### Scenario: 快捷跳转审批
- **WHEN** 用户点击指挥台中的某个待审批事项
- **THEN** 跳转到 `/approvals/{approval_id}` 审批详情页

### Requirement: 失败工作流入口
风险指挥台 SHALL 展示失败/待恢复工作流的数量和快捷入口。

#### Scenario: 查看失败工作流
- **WHEN** 用户点击"失败工作流"卡片
- **THEN** 跳转到 `/workflows?status=FAILED_RETRYABLE` 筛选后的工作流列表
