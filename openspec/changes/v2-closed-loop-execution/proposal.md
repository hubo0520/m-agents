## Why

阶段 1（merchant-risk-agent-mvp）已实现风险发现 + 人工审批闭环，但审批通过后的执行动作（融资申请、理赔申请、人工复核任务）仍需运营人员手动完成。
阶段 2 的核心目标是：**系统根据风险评估自动生成执行任务（融资申请草稿、理赔申请草稿、人工复核任务），并推送给对应角色处理，将案件平均处理时间从 30 分钟缩短至 10 分钟**。

## What Changes

### 后端新增
- 新增 3 张数据库表：`financing_applications`（融资申请）、`claims`（理赔申请）、`manual_reviews`（人工复核任务）
- 新增 **任务生成引擎**（`services/task_generator.py`），根据 Recommendation + 规则引擎自动生成对应执行任务
- 新增 **规则引擎**（`engine/rules.py`），负责融资资格判断、理赔材料匹配和复核触发条件匹配
- 新增 3 个 REST API 端点：手动触发生成融资/理赔/复核任务（`POST /api/risk-cases/{case_id}/generate-financing-application`、`generate-claim-application`、`generate-manual-review`）
- 新增任务列表查询 API（`GET /api/tasks`），支持按类型/状态/负责人筛选
- 新增任务详情 + 状态流转 API（审核通过/驳回/完成）
- 扩展 Orchestrator 编排层：在 Agent 分析完成后自动调用任务生成引擎，生成待审核的执行任务

### 后端修改
- 扩展 `RiskCase` 模型，增加关联到执行任务的关系
- 扩展审批服务（`services/approval.py`），支持在审批通过时自动触发任务生成
- 扩展 `Recommendation` 模型，增加 `task_generated` 标记和关联任务 ID

### 前端新增
- 新增 **任务管理页面**（`/tasks`），展示所有执行任务的看板视图（待处理/处理中/已完成）
- 新增融资申请详情页，展示自动填充的草稿内容，支持编辑和提交
- 新增理赔申请详情页，展示自动填充的草稿内容，支持编辑和提交
- 新增人工复核任务详情页，展示复核理由、证据、复核结果录入

### 前端修改
- 案件详情页增加"执行任务"Tab，展示该案件关联的所有任务
- 案件详情页审批通过后显示"已自动生成执行任务"状态提示
- 导航栏增加"任务管理"入口

## Capabilities

### New Capabilities
- `financing-application`: 自动生成融资申请草稿，包含商家信息、资金需求、历史回款、还款计划等
- `claim-application`: 自动生成理赔申请草稿，包含退货原因、退款金额、物流证据等
- `manual-review-task`: 自动生成人工复核任务，包含复核理由、关联证据、分配给指定运营人员
- `task-management`: 任务管理看板，支持任务列表/详情/状态流转/筛选
- `rule-engine`: 规则引擎，负责融资资格判断、理赔条件匹配、复核触发条件评估

### Modified Capabilities
- （无需修改现有 spec 级别行为，V2 新功能均为增量扩展）

## Impact

### 数据库
- 新增 3 张表（`financing_applications`、`claims`、`manual_reviews`）
- `recommendations` 表新增 `task_generated`、`task_type`、`task_id` 字段
- `risk_cases` 表新增关系到执行任务

### API
- 新增 6+ 个 REST 端点（任务生成、任务列表、任务详情、任务状态流转）
- 现有 `/api/risk-cases/{case_id}/review` 端点行为扩展（审批通过后触发任务生成）

### 依赖
- 后端无新增第三方依赖，复用现有 FastAPI + SQLAlchemy 技术栈
- 前端复用现有 Next.js + Tailwind CSS 技术栈

### 影响的现有文件
- `backend/app/models/models.py` — 新增 3 个模型 + 扩展 Recommendation
- `backend/app/agents/orchestrator.py` — 分析完成后自动触发任务生成
- `backend/app/services/approval.py` — 审批通过后触发任务生成
- `backend/app/api/risk_cases.py` — 新增任务生成端点
- `backend/app/schemas/schemas.py` — 新增任务相关 Schema
- `frontend/src/app/page.tsx` — 导航栏新增入口
- `frontend/src/app/cases/[id]/page.tsx` — 增加执行任务 Tab
