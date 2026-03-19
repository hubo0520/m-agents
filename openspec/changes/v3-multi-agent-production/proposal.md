## Why

阶段 1（MVP）实现了风险发现 + 人工审批闭环，阶段 2 实现了审批通过后自动生成执行任务（融资/理赔/复核）。但当前系统仍是"单 Agent + 顺序执行"架构：所有分析集中在一个 Orchestrator 内，无法暂停/恢复长流程，审批与执行缺少统一门禁，LLM 输出缺乏版本追踪和评测能力，节点失败会导致整条链路崩溃。

阶段 3 的核心目标是：**将系统从"单案件分析工具"升级为"可持续运行的多 Agent 风控执行系统"**，支持多 Agent 协同编排（LangGraph）、长流程可暂停恢复、强审批门禁、生产级观测与评测，使高风险案件首响时间下降 70%，单案件处理时长下降 50%。

## What Changes

### 后端新增——Agent 编排层（LangGraph）
- 新增 `workflow/` 模块，基于 LangGraph 构建显式 graph 编排引擎
- 新增 9 个 specialist Agent 节点：Monitor、Triage、Diagnosis、Forecast、Recommendation、Evidence、Compliance Guard、Execution、Summary
- 新增 14 个 graph 节点：`load_case_context` → `triage_case` → `compute_metrics` → `forecast_gap` → `diagnose_case` → `collect_evidence` → `generate_recommendations` → `run_guardrails` → `create_approval_tasks` → `wait_for_approval` → `execute_actions` → `wait_external_callback` → `finalize_summary` → `write_audit_log`
- 新增案件状态机：NEW → TRIAGED → ANALYZING → RECOMMENDING → PENDING_APPROVAL → EXECUTING → WAITING_CALLBACK → COMPLETED，含异常分支（NEEDS_MORE_DATA、BLOCKED_BY_GUARD、REJECTED、FAILED_RETRYABLE、FAILED_FINAL、PAUSED → RESUMED）

### 后端新增——工作流持久化与恢复
- 新增 `workflow_runs` 表，记录每次工作流运行状态、当前节点、暂停/恢复时间
- 新增 `checkpoints` 表，存储 LangGraph checkpoint 用于故障恢复
- 新增 `agent_runs` 表，记录每个 Agent 节点的输入/输出/模型版本/延迟
- 支持服务重启后从 checkpoint 恢复，审批完成后从中断点继续

### 后端新增——审批中心
- 新增 `approval_tasks` 表，统一管理所有审批事项（经营贷、回款加速、反欺诈复核、理赔提交）
- 新增审批 API：列表、详情、批准、驳回、修改后批准
- 审批完成自动恢复关联 workflow，驳回进入 REJECTED/REWORK
- 支持 SLA 超时提醒

### 后端新增——工具注册与连接器
- 新增 `tool_invocations` 表，记录所有工具调用日志
- 新增工具注册中心，每个工具具备 `tool_name`、`version`、`approval_policy`
- 支持幂等键、审批前置拦截

### 后端新增——版本管理与评测
- 新增 `prompt_versions` 表，管理 Agent Prompt 版本
- 新增 `schema_versions` 表，管理 Agent 输出 Schema 版本
- 新增 `eval_datasets` / `eval_runs` / `eval_results` 表，支持离线评测与线上抽样
- 所有 agent_run 绑定 model_name、prompt_version、schema_version

### 后端新增——失败回退与重试
- Agent 节点失败可回退到规则建议模式
- 外部工具失败可进入人工处理
- 所有失败写入 audit_logs 与 workflow_runs
- 支持 retryable 任务手动/自动重试

### 后端新增——权限控制
- 新增基于角色的访问控制（风险运营、融资运营、理赔运营、合规复核、管理员）
- 不同角色只能访问允许的案件、审批和配置项

### 后端修改
- 重构 `agents/orchestrator.py`，将单体 Orchestrator 拆分为 LangGraph 节点
- 扩展现有 Agent（analysis_agent、recommend_agent、evidence_agent、guardrail），使其符合 Agent 输入输出契约（Pydantic schema）
- 扩展 `models/models.py`，新增 8+ 张表
- 所有 LLM 输出改用 OpenAI Structured Outputs

### 前端新增
- 新增 **审批中心页面**（`/approvals`），展示待审批任务列表、详情、一键批准/驳回/修改后批准、批量审批、SLA 倒计时
- 新增 **工作流运行中心页面**（`/workflows`），展示 workflow_run 列表、当前节点、节点耗时、中断原因、恢复入口、失败回溯
- 新增 **规则与模型中心页面**（`/settings`），管理 prompt version、schema version、model policy、tool allowlist、审批策略
- 新增 **评测中心页面**（`/evals`），管理评测集、运行评测、查看采纳率/幻觉率/证据覆盖率

### 前端修改
- 风险看板升级为**风险指挥台**，新增处理中案件、高优先级待审批事项、失败/待恢复工作流数
- 案件详情页升级为**案件工作台**，新增子 Agent 输出折叠区、证据绑定展示
- 导航栏新增 审批中心 / 工作流 / 设置 / 评测 入口

## Capabilities

### New Capabilities
- `langgraph-workflow-engine`: LangGraph 多 Agent 编排引擎，显式 graph 定义、条件分支、节点失败重试/人工接管
- `workflow-persistence`: 工作流持久化与恢复，checkpoint 落库、服务重启恢复、审批后从中断点继续
- `approval-center`: 审批中心，统一审批队列、批准/驳回/修改后批准、批量审批、SLA 超时提醒、审批后自动恢复 workflow
- `tool-registry`: 工具与连接器注册中心，统一工具注册、权限策略、幂等键、调用日志
- `agent-contracts`: Agent 输入输出契约，所有 Agent 通用输入结构 + 各 Agent Pydantic 输出 schema + Structured Outputs
- `version-management`: Prompt / Schema / Model 版本管理，灰度开关、回滚能力
- `eval-center`: 评测中心，离线评测集、线上抽样、采纳率/幻觉率/证据覆盖率/schema 合格率
- `failure-recovery`: 失败回退与重试，LLM 节点降级到规则模式、外部工具失败人工接管、retryable 重试
- `rbac-permissions`: 基于角色的权限控制，5 种角色（风险运营、融资运营、理赔运营、合规复核、管理员）
- `risk-command-center`: 风险指挥台前端，升级看板为带审批/工作流/失败恢复统计的指挥中心
- `workflow-monitor-ui`: 工作流运行中心前端，展示 run 列表、节点耗时、失败回溯、恢复入口
- `settings-center-ui`: 规则与模型中心前端，管理 prompt/schema 版本、模型策略、工具配置、审批规则

### Modified Capabilities
- `agent-orchestrator`: 从单体 Orchestrator 重构为 LangGraph 多节点图编排，保留原有分析/推荐/证据/守卫逻辑但拆分为独立 Agent
- `approval-workflow`: 从简单案件审批扩展为统一审批中心，支持 workflow 级别的审批门禁和自动恢复
- `rest-api`: 新增 workflow / approval / config / eval 四组 API 端点

## Impact

### 数据库
- 新增 8+ 张表：`workflow_runs`、`agent_runs`、`checkpoints`、`approval_tasks`、`tool_invocations`、`prompt_versions`、`schema_versions`、`eval_datasets`/`eval_runs`/`eval_results`
- 现有表结构保持不变，增量扩展

### API
- 新增 20+ 个 REST 端点（workflow 管理 7 个 + 审批 5 个 + 配置 4 个 + 评测 3 个 + 其他）
- 现有 API 保持兼容，扩展案件详情返回 workflow 信息

### 依赖
- 后端新增：`langgraph`（编排引擎）、`langgraph-checkpoint-sqlite`（checkpoint 持久化）
- 后端保留：FastAPI、SQLAlchemy、Pydantic、OpenAI SDK
- 前端保留：Next.js、TypeScript、Tailwind CSS

### 影响的现有文件
- `backend/app/agents/orchestrator.py` — 重构为 LangGraph 节点调度
- `backend/app/agents/analysis_agent.py` — 适配 Agent 契约接口
- `backend/app/agents/recommend_agent.py` — 适配 Agent 契约接口
- `backend/app/agents/evidence_agent.py` — 适配 Agent 契约接口
- `backend/app/agents/guardrail.py` — 适配 Guard Agent 契约接口
- `backend/app/models/models.py` — 新增 8+ 张表模型
- `backend/app/main.py` — 注册新 router
- `frontend/src/app/layout.tsx` — 导航栏新增入口
- `frontend/src/app/page.tsx` — 升级为风险指挥台
- `frontend/src/app/cases/[id]/page.tsx` — 增加子 Agent 输出折叠区
- `frontend/src/lib/api.ts` — 新增 workflow / approval / config / eval API 客户端
- `frontend/src/types/index.ts` — 新增相关类型定义
