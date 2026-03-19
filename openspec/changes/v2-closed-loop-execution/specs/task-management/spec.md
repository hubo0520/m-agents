## ADDED Requirements

### Requirement: 统一任务列表查询
系统 SHALL 提供 `GET /api/tasks` 端点，支持跨类型查询所有执行任务（融资申请、理赔申请、人工复核），返回统一格式的任务列表。

#### Scenario: 查询全部任务
- **WHEN** 运营人员访问任务管理页面，未设置筛选条件
- **THEN** 系统返回所有类型的任务列表，每条记录包含 task_id、task_type（financing/claim/manual_review）、merchant_name、status、created_at、assigned_to，按 created_at 降序排列

#### Scenario: 按类型筛选任务
- **WHEN** 运营人员选择筛选条件 task_type=financing
- **THEN** 系统仅返回融资申请类型的任务

#### Scenario: 按状态筛选任务
- **WHEN** 运营人员选择筛选条件 status=PENDING_REVIEW
- **THEN** 系统返回所有状态为 PENDING_REVIEW 的任务（跨类型）

#### Scenario: 按负责人筛选任务
- **WHEN** 运营人员选择筛选条件 assigned_to=ops_user_1
- **THEN** 系统返回分配给该运营人员的所有任务

### Requirement: 任务详情查询
系统 SHALL 提供 `GET /api/tasks/{task_type}/{task_id}` 端点，返回特定任务的完整详情，包含关联的案件信息和商家信息。

#### Scenario: 查询融资申请详情
- **WHEN** 运营人员点击融资申请任务
- **THEN** 系统返回融资申请的完整信息，包括商家快照、资金需求、还款计划、关联案件 ID

#### Scenario: 查询不存在的任务
- **WHEN** 运营人员查询一个不存在的 task_id
- **THEN** 系统返回 404 错误

### Requirement: 任务状态更新
系统 SHALL 提供 `PUT /api/tasks/{task_type}/{task_id}/status` 端点，支持运营人员更新任务状态。

#### Scenario: 更新任务状态
- **WHEN** 运营人员提交状态更新请求，包含 new_status 和可选的 comment
- **THEN** 系统验证状态流转合法性，更新状态，记录审计日志

#### Scenario: 非法状态流转
- **WHEN** 运营人员尝试将 COMPLETED 状态的任务改为 DRAFT
- **THEN** 系统返回 400 错误，提示"不允许的状态流转"

### Requirement: 任务管理看板页面
前端 SHALL 提供 `/tasks` 页面，展示所有执行任务的看板视图，支持按状态分列展示（待处理/处理中/已完成）。

#### Scenario: 看板展示
- **WHEN** 运营人员访问 /tasks 页面
- **THEN** 页面展示三列看板：待处理（DRAFT + PENDING_REVIEW + PENDING）、处理中（IN_PROGRESS + EXECUTING）、已完成（COMPLETED + APPROVED + REJECTED + CLOSED），每列显示任务卡片

#### Scenario: 任务卡片点击跳转
- **WHEN** 运营人员点击任务卡片
- **THEN** 页面跳转到对应类型的任务详情页

#### Scenario: 看板筛选
- **WHEN** 运营人员在看板页面选择筛选条件
- **THEN** 所有列同步更新显示符合条件的任务

### Requirement: 案件详情页展示关联任务
前端案件详情页 SHALL 增加"执行任务"Tab，展示该案件关联的所有执行任务。

#### Scenario: 展示关联任务列表
- **WHEN** 运营人员在案件详情页切换到"执行任务"Tab
- **THEN** 页面展示该案件生成的所有任务列表，包含任务类型、状态和创建时间

#### Scenario: 审批通过后显示任务生成提示
- **WHEN** 案件审批通过且系统已自动生成执行任务
- **THEN** 案件详情页顶部显示"已自动生成 N 条执行任务"提示条
