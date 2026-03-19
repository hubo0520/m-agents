## MODIFIED Requirements

### Requirement: 新增 Workflow 管理 API
系统 SHALL 新增以下 workflow 管理 API 端点：
- POST /api/workflows/start — 启动新 workflow
- POST /api/workflows/{run_id}/resume — 恢复暂停的 workflow
- POST /api/workflows/{run_id}/retry — 重试失败的 workflow
- GET /api/workflows/{run_id} — 获取 workflow 详情
- GET /api/workflows/{run_id}/trace — 获取 workflow 执行轨迹
- GET /api/cases/{case_id}/latest-run — 获取案件最新 workflow run
- POST /api/cases/{case_id}/reopen — 重开已完成/驳回的案件

#### Scenario: 启动新 workflow
- **WHEN** 调用 POST /api/workflows/start 传入 case_id
- **THEN** 创建 workflow_run 记录，启动 LangGraph 执行，返回 run_id

#### Scenario: 重试失败 workflow
- **WHEN** 调用 POST /api/workflows/{run_id}/retry
- **THEN** 从 checkpoint 恢复状态，从失败节点重新执行

### Requirement: 新增审批 API
系统 SHALL 新增以下审批 API 端点：
- GET /api/approvals — 审批列表（支持按 status、approval_type 筛选）
- GET /api/approvals/{approval_id} — 审批详情
- POST /api/approvals/{approval_id}/approve — 批准
- POST /api/approvals/{approval_id}/reject — 驳回
- POST /api/approvals/{approval_id}/revise-and-approve — 修改后批准

#### Scenario: 获取待审批列表
- **WHEN** 调用 GET /api/approvals?status=PENDING
- **THEN** 返回所有待审批任务列表

### Requirement: 新增配置管理 API
系统 SHALL 新增以下配置管理 API 端点：
- GET /api/agent-configs — 获取 Agent 配置列表
- POST /api/prompt-versions — 创建 prompt 版本
- POST /api/schema-versions — 创建 schema 版本
- POST /api/model-policies — 创建模型策略

#### Scenario: 创建新 prompt 版本
- **WHEN** 调用 POST /api/prompt-versions 传入 agent_name、content
- **THEN** 创建 prompt_versions 记录，返回版本信息

### Requirement: 新增评测 API
系统 SHALL 新增以下评测 API 端点：
- POST /api/evals/datasets — 创建评测数据集
- POST /api/evals/runs — 启动评测运行
- GET /api/evals/runs/{eval_run_id} — 获取评测结果

#### Scenario: 创建评测数据集
- **WHEN** 调用 POST /api/evals/datasets 传入 name 和 test_cases
- **THEN** 创建 eval_datasets 记录

### Requirement: 现有 API 保持兼容
现有 `/api/risk-cases` 和 `/api/tasks` 系列 API SHALL 保持完全向后兼容，案件详情返回额外的 workflow 信息。

#### Scenario: 旧 API 正常访问
- **WHEN** 调用 GET /api/risk-cases
- **THEN** 返回与 V2 相同格式的案件列表，额外包含 latest_workflow_status 字段
