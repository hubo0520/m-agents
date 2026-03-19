## Context

商家经营保障 Agent V1（merchant-risk-agent-mvp）已上线，实现了风险发现 → Agent 分析 → 人工审批的完整流程。当前技术栈：

- **后端**：FastAPI + SQLAlchemy + SQLite，包含 12 张业务表、7 个核心指标计算函数、14 日现金缺口预测、Agent 编排层（Mock LLM）、审批服务、导出服务
- **前端**：Next.js 14 + Tailwind CSS + Recharts，包含风险看板和案件详情两个页面
- **当前瓶颈**：审批通过后，运营人员需手动执行融资申请、理赔申请和复核任务。本次升级要将这些手动操作自动化。

约束：
- 继承现有 monorepo 结构（`backend/` + `frontend/`）
- 继续使用 SQLite（MVP 阶段），不引入新的外部依赖
- Agent 编排层继续使用 Mock 实现，不接入真实 LLM
- 新增功能以增量方式扩展，不破坏现有接口

## Goals / Non-Goals

**Goals:**
- 审批通过后自动生成融资申请草稿、理赔申请草稿、人工复核任务
- 规则引擎自动判断商家是否符合融资/理赔资格，并填充申请材料
- 提供任务管理看板，支持运营人员查看、处理所有执行任务
- 完整审计记录：每个自动生成的任务都有可追溯的来源链（案件→建议→任务）
- 任务状态机：`DRAFT → PENDING_REVIEW → APPROVED → EXECUTING → COMPLETED / REJECTED`

**Non-Goals:**
- 不做自动放款/自动理赔决策（所有执行仍需人工确认）
- 不接入真实外部融资/理赔系统（仅生成草稿）
- 不做实时风险监控或流式推送
- 不增加用户端（商家端）功能

## Decisions

### D1: 任务生成采用"事件驱动 + 手动触发"双模式

**决策**：任务生成支持两种触发方式：
1. **自动触发**：审批通过时，Orchestrator 自动调用任务生成引擎
2. **手动触发**：通过 API 端点手动触发生成（`POST /api/risk-cases/{case_id}/generate-*`）

**理由**：自动触发提升效率，手动触发保留灵活性。运营人员可以在审批前预览生成结果，也可以跳过自动生成手动创建。

**替代方案**：
- 仅自动触发 → 无法处理需要人工介入的特殊场景
- 仅手动触发 → 与 V1 无本质区别，不符合"闭环执行"目标

### D2: 规则引擎采用 Python 函数 + JSON 配置混合模式

**决策**：
- 核心判断逻辑（融资资格、理赔条件）用 Python 函数实现（`engine/rules.py`）
- 阈值和参数存储在 `financing_products.eligibility_rule_json` 和新增的配置表中
- 不引入独立的规则引擎框架

**理由**：
- V1 已有 `financing_products.eligibility_rule_json` 字段，可直接复用
- 规则数量有限（<20条），不需要复杂的规则引擎
- Python 函数易于调试和单元测试

**替代方案**：
- 引入 Drools/RETE 引擎 → 过度设计，增加运维复杂度
- 纯 JSON 配置 → 复杂逻辑（如多条件组合判断）表达困难

### D3: 三类任务统一抽象 + 分表存储

**决策**：融资申请、理赔申请、人工复核任务分别存储在独立表中（`financing_applications`、`claims`、`manual_reviews`），但通过统一的任务查询 API 提供聚合视图。

**理由**：
- 三类任务字段差异大（融资有金额/期限，理赔有原因/证据，复核有分配人）
- 分表存储更清晰，避免大量 nullable 字段
- API 层通过 UNION 查询或内存聚合提供统一视图

**替代方案**：
- 单表+type 字段 → 大量 nullable 字段，查询时需要 type 过滤
- 多态继承（SQLAlchemy） → 增加 ORM 复杂度

### D4: Recommendation 与 Task 的关联方式

**决策**：在 `Recommendation` 模型上新增 `task_generated`（bool）、`task_type`（string）、`task_id`（int）字段，建立 Recommendation → Task 的单向关联。

**理由**：
- 一个 Recommendation 最多生成一个执行任务
- 通过 task_type + task_id 实现多态关联（type 标识目标表）
- 查询案件时可以快速知道哪些建议已经生成了任务

### D5: 前端任务管理页采用看板视图

**决策**：任务管理页面采用看板（Kanban）布局，按状态分列展示：待处理 → 处理中 → 已完成。

**理由**：
- 运营人员习惯看板视图，一目了然
- 状态流转通过拖拽或按钮操作
- 与现有风险看板页面风格一致

## Risks / Trade-offs

**[R1] SQLite 并发写入限制** → 
当前 SQLite 在高并发写入场景下可能出现锁等待。V2 新增的任务生成会增加写入量。
**缓解**：MVP 阶段单用户使用足够；后续可迁移至 PostgreSQL。

**[R2] 规则引擎硬编码风险** →
规则以 Python 函数形式存在，修改规则需要重新部署。
**缓解**：阈值参数通过 JSON 配置，核心逻辑变更频率低；后续可引入规则配置 UI。

**[R3] 任务生成的幂等性** →
同一个 Recommendation 重复触发可能生成多个任务。
**缓解**：在 `Recommendation.task_generated` 标记上做幂等检查，已生成则跳过。

**[R4] 前端状态同步** →
任务状态在后端变更后前端可能展示旧数据。
**缓解**：任务列表页设置自动刷新（30s 轮询）；详情页操作后立即重新拉取。
