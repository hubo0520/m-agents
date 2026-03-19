## Context

当前系统（V1 MVP + V2 闭环执行）架构：
- **后端**：FastAPI + SQLAlchemy + SQLite，单体 Orchestrator 编排 4 个逻辑子 Agent（分析/推荐/证据/守卫）
- **前端**：Next.js + TypeScript + Tailwind CSS，3 个核心页面（风险看板/案件详情/任务管理）
- **数据库**：15 张表（V1 12 张 + V2 3 张），SQLite 存储
- **工作流**：同步执行，无持久化，审批仅支持案件级别的简单状态流转

V3 需要将系统升级为多 Agent 协同的生产级执行系统，同时 **保持与现有 backend/ 和 frontend/ 目录结构的完全兼容**。

**约束条件**：
- 继承现有 monorepo 结构（`backend/` + `frontend/`）
- 继续使用 SQLite（开发阶段），但 schema 设计需兼容 PostgreSQL 迁移
- LLM 调用使用 OpenAI Responses API + Structured Outputs
- LangGraph 仅做编排，不做业务计算
- 数值指标来自 domain service，不来自 LLM

## Goals / Non-Goals

**Goals:**
- 将单体 Orchestrator 拆分为 9 个 specialist Agent，通过 LangGraph 显式 graph 编排
- 实现工作流持久化与恢复，支持跨分钟/小时/天级暂停和恢复
- 建立统一审批中心，所有敏感动作必须经过审批门禁
- 实现工具注册中心，统一管理工具调用权限和审计
- 实现 Prompt / Schema / Model 版本管理，支持灰度和回滚
- 建立评测中心，支持离线评测和线上抽样
- 实现失败回退与重试机制，节点失败不崩全链
- 建立基于角色的权限控制
- 前端新增 4 个工作台页面（审批中心/工作流运行/设置中心/评测中心）

**Non-Goals:**
- 全自动放款 / 全自动拒赔 / 自动改价并直接生效
- 完整 SaaS 多租户商业化
- 端到端无人值守金融决策
- 数据库迁移到 PostgreSQL（本阶段仍用 SQLite，但设计兼容）
- 真实外部系统集成（使用 mock connector，至少 1 个读 + 1 个写前审批）

## Decisions

### Decision 1: 编排引擎选择 LangGraph

**选择**: LangGraph 作为多 Agent 编排引擎

**理由**:
- 显式 graph 编排适合金融场景的确定性流程控制
- 内置 durable execution 和 checkpointer，天然支持暂停/恢复
- 人审（human-in-the-loop）作为一等公民，与审批需求完美匹配
- 状态持久化和调试能力满足生产级观测需求

**替代方案**:
- CrewAI / AutoGen：自主度过高，金融场景需要确定性流程
- 纯代码状态机：缺少 checkpoint、replay、中断恢复等能力
- OpenAI Agents SDK：主要面向单 Agent + tools 模式，graph 编排能力不足

**实现**:
- 新增 `backend/app/workflow/` 模块
- 使用 `langgraph` + `langgraph-checkpoint-sqlite` 依赖
- graph 定义在 `workflow/graph.py`，节点实现在 `workflow/nodes/` 目录

### Decision 2: Agent 拆分策略——渐进式重构

**选择**: 保留现有 Agent 代码，包装为 LangGraph 节点

**理由**:
- 现有 `analysis_agent.py`、`recommend_agent.py`、`evidence_agent.py`、`guardrail.py` 逻辑已验证
- 新增 Agent（Monitor、Triage、Forecast、Compliance Guard、Execution、Summary）以独立文件实现
- 通过适配器模式将旧 Agent 包装为符合统一输入输出契约的节点

**实现**:
- 现有 `agents/` 目录保留，新增 `agents/triage_agent.py`、`agents/compliance_agent.py`、`agents/execution_agent.py`、`agents/summary_agent.py`
- `agents/schemas.py` 扩展为完整的 Agent 输入输出契约（Pydantic）
- `workflow/nodes/` 中编写节点封装，调用 agents 模块

### Decision 3: 审批系统设计——统一审批队列

**选择**: 新建 `approval_tasks` 表 + 独立 API 模块，取代现有简单 review 机制

**理由**:
- V2 的审批仅限案件级别，无法覆盖 workflow 级审批需求
- 需要支持多种审批类型（经营贷、回款加速、反欺诈复核、理赔提交）
- 需要与 LangGraph 的 interrupt/resume 机制集成

**实现**:
- `approval_tasks` 表关联 `workflow_run_id`，审批通过后自动触发 graph resume
- 保留现有 `reviews` 表用于案件级审批（向后兼容）
- 新增 `api/approvals.py` 模块

### Decision 4: Checkpoint 存储——SQLite + Blob

**选择**: 使用 `langgraph-checkpoint-sqlite` 将 checkpoint 存入 SQLite

**理由**:
- 与现有 SQLite 数据库统一，部署简单
- LangGraph 官方提供 SQLite checkpoint 实现
- 未来迁移 PostgreSQL 时可切换为 `langgraph-checkpoint-postgres`

**替代方案**:
- Redis：增加额外依赖，开发环境复杂度上升
- 文件系统：不支持并发，不利于查询

### Decision 5: 前端页面组织——Tab 模式扩展

**选择**: 新增 4 个顶级路由页面，复用现有布局组件

**理由**:
- 继承现有 `layout.tsx` 导航结构，增量添加菜单项
- 审批中心（`/approvals`）、工作流（`/workflows`）、设置（`/settings`）、评测（`/evals`）作为独立页面
- 风险看板升级为指挥台，案件详情页增加子 Agent 输出折叠区

**实现**:
- 新增 `frontend/src/app/approvals/page.tsx`
- 新增 `frontend/src/app/workflows/page.tsx`
- 新增 `frontend/src/app/settings/page.tsx`
- 新增 `frontend/src/app/evals/page.tsx`

### Decision 6: 所有 LLM 输出采用 Structured Outputs

**选择**: 所有 Agent 间通信和落库结果使用 OpenAI Structured Outputs + Pydantic schema

**理由**:
- OpenAI Structured Outputs 能保证输出严格遵守 schema
- 比 JSON mode 更可靠，直接与 Pydantic 模型绑定
- 便于版本管理和回归评测

**实现**:
- 每个 Agent 定义独立的 Pydantic 输出 schema
- `schema_versions` 表记录版本历史
- Agent run 记录关联使用的 schema_version

### Decision 7: 失败回退策略——分级降级

**选择**: 三级降级策略（重试 → 规则降级 → 人工接管）

**理由**:
- 金融场景不允许链路完全崩溃
- LLM 节点故障概率较高（超时/限流/幻觉），需要明确降级路径

**实现**:
- L1：自动重试（最多 3 次，指数退避）
- L2：LLM 节点失败 → 切换到规则引擎（现有 `engine/rules.py`）
- L3：规则引擎也失败 → 创建人工处理任务
- 所有失败记录写入 `workflow_runs.status = FAILED_RETRYABLE / FAILED_FINAL`

## Risks / Trade-offs

### [LangGraph 学习曲线] → 通过渐进式重构降低风险
- 先实现最简 graph（4 个核心节点），再逐步拆分完整 9-Agent 架构
- 保留现有 Orchestrator 作为 fallback 路径

### [数据库表增长过快] → 只新增必要表，延迟创建可选表
- 核心表优先：`workflow_runs`、`agent_runs`、`checkpoints`、`approval_tasks`
- 延迟创建：`eval_datasets`/`eval_runs`/`eval_results` 可在评测功能完善后再建

### [Checkpoint 存储膨胀] → 设置 TTL + 归档策略
- 已完成的 workflow checkpoint 保留 7 天后清理
- 失败/暂停的 checkpoint 保留 30 天

### [Structured Outputs 限制] → 使用 JSON Schema 子集
- 某些复杂嵌套 schema 可能超出 Structured Outputs 支持范围
- 对超复杂输出降级为 JSON mode + schema 校验

### [前端页面数量翻倍] → 组件复用 + 统一设计语言
- 抽取通用组件（表格、状态标签、时间线、审批按钮）
- 统一使用现有 Tailwind 设计风格

## Open Questions

1. **Monitor Agent 是否需要 LLM**：V3 PRD 建议"优先非 LLM，由规则+指标函数驱动"，是否完全不用 LLM？
2. **真实连接器范围**：PRD 要求"至少 1 个读、1 个写前审批"，具体对接哪个外部系统？建议先 mock 全部，标记 1 个读（查询商家信用评分）+ 1 个写（提交回款加速申请）为可替换为真实连接器。
3. **权限控制粒度**：是否需要完整 RBAC 表结构，还是先用硬编码角色 + 简单中间件？建议先用中间件 + 配置文件，后续按需升级。
