## Context

当前平台商家经营数据散落在订单、退货、物流、回款、保险、融资多个子系统，运营人员只能通过静态报表逐一排查，无法快速识别"退货激增 → 现金流缺口"的连锁风险。本项目构建第一版 MVP，作为内部运营 Web 系统，实现从"风险发现"到"审批处置"的全流程自动化工作台。

**当前状态**：零基础新建项目，无历史代码负担。

**约束条件**：
- 第一阶段使用 SQLite（便于本地开发），不对接真实支付/放款/理赔系统
- 不使用向量数据库、不做 ML 训练、不做复杂消息队列
- 所有数值分析由 Python 函数完成，禁止 LLM 编造数字
- Agent 输出必须为可校验 JSON，所有建议带 evidence_ids
- 涉及融资和反欺诈的建议必须 requires_manual_review=true

**利益相关者**：风险运营（主要用户）、融资运营（关注资金缺口和融资建议）、管理员（配置与审计）

## Goals / Non-Goals

**Goals:**
- 构建可本地运行的全栈 MVP，覆盖风险案件"发现→分析→建议→审批→导出"闭环
- 前后端完全分离，前端 Next.js + TypeScript + Tailwind，后端 FastAPI + SQLite
- 数值分析引擎纯 Python 实现，14 日现金缺口预测使用滚动均值 + 季节性系数
- Agent 编排层使用 Orchestrator + 4 个逻辑子 Agent 模式，第一阶段使用 mock 响应
- Mock 数据生成器覆盖 50 个商家 × 90 天 × 3 类风险场景
- 完整审批流与审计日志

**Non-Goals:**
- 不对接真实 LLM 服务（第一阶段使用 mock Agent 响应）
- 不对接真实支付、放款、理赔系统
- 不使用向量数据库或知识库
- 不做自动放款/自动拒赔/自动修改保险定价
- 不做商家端自助入口
- 不做手机端适配
- 不做 ML 模型训练

## Decisions

### 决策 1：Monorepo 项目结构

**选择**：单仓库（monorepo），`frontend/` 和 `backend/` 两个子目录

**原因**：MVP 阶段代码量有限，单仓库便于开发调试和版本管理。前后端在同一仓库中可以共享类型定义思路和 API 契约。

**备选方案**：
- 多仓库分别管理前后端 → 增加维护成本，MVP 阶段不必要
- 完整 monorepo 工具链（turborepo/nx）→ 过度工程化

**目录结构**：
```
m-agents/
├── frontend/                # Next.js 应用
│   ├── src/
│   │   ├── app/            # App Router 页面
│   │   ├── components/     # UI 组件
│   │   ├── lib/            # 工具函数和 API 客户端
│   │   └── types/          # TypeScript 类型定义
│   ├── package.json
│   ├── tailwind.config.ts
│   └── tsconfig.json
├── backend/                 # FastAPI 应用
│   ├── app/
│   │   ├── api/            # 路由层
│   │   ├── models/         # SQLAlchemy 模型
│   │   ├── schemas/        # Pydantic 模型
│   │   ├── services/       # 业务逻辑
│   │   ├── agents/         # Agent 编排
│   │   ├── engine/         # 数值分析引擎
│   │   └── core/           # 配置和公共模块
│   ├── scripts/            # 数据生成和迁移脚本
│   ├── tests/              # 测试
│   └── requirements.txt
├── agent.md                 # 产品需求文档
└── openspec/               # 变更管理
```

### 决策 2：数据库选择 SQLite

**选择**：开发阶段使用 SQLite，通过 SQLAlchemy ORM 抽象

**原因**：
- 零配置，本地直接运行
- MVP 数据量小（50 商家 × 90 天），SQLite 完全胜任
- SQLAlchemy 抽象层使未来迁移到 PostgreSQL 只需改连接字符串

**备选方案**：
- 直接用 PostgreSQL → 增加开发环境配置成本
- 用内存数据库 → 数据不持久化，不利于调试

### 决策 3：Agent 架构 — Orchestrator + 逻辑子 Agent

**选择**：单进程 Orchestrator 函数 + 4 个逻辑子 Agent（分析/推荐/证据/守卫），第一阶段全部 mock

**原因**：
- 文档明确要求"不要真的上复杂分布式多 Agent"
- 4 个子 Agent 映射为 4 个 Python 模块，函数调用即可
- Mock 模式下直接返回基于规则生成的结构化 JSON
- 未来接入真实 LLM 只需替换各子 Agent 的实现函数

**备选方案**：
- LangChain/LangGraph 多 Agent → 过早引入框架复杂度
- 单个大函数 → 职责不清晰，不利于后续扩展

**Agent 调用流程**：
```
定时任务/手动触发
    ↓
Orchestrator.analyze(case_id)
    ├─ MetricsEngine.compute(merchant_id)     # 数值计算
    ├─ EvidenceAgent.collect(case_id)         # 收集证据
    ├─ AnalysisAgent.summarize(context)       # 生成摘要
    ├─ RecommendAgent.suggest(context)        # 生成建议
    └─ GuardrailEngine.validate(output)       # 校验守卫
    ↓
保存到数据库 → 更新案件状态为 ANALYZED
```

### 决策 4：数值分析引擎独立于 Agent

**选择**：所有核心指标由 `backend/app/engine/` 下的纯 Python 函数计算

**原因**：
- 产品文档明确要求"数值由后端函数生成，不允许由 LLM 直接编造"
- 指标函数可独立单元测试
- Agent 只消费指标结果，不参与计算

**核心指标函数**：
- `compute_return_rate(merchant_id, days)` → 退货率
- `compute_baseline_return_rate(merchant_id)` → 28 日基线退货率
- `compute_return_amplification(merchant_id)` → 退货率放大倍数
- `compute_avg_settlement_delay(merchant_id)` → 平均回款延迟
- `compute_refund_pressure(merchant_id, days)` → 退款压力
- `forecast_cash_gap(merchant_id, horizon_days)` → 14 日现金缺口预测
- `compute_anomaly_score(merchant_id)` → 异常退货分数

### 决策 5：前端路由与数据获取

**选择**：Next.js App Router + 客户端 fetch 调用后端 API

**原因**：
- App Router 是 Next.js 推荐的路由方式
- 前后端完全分离，前端不做 SSR 数据获取（避免复杂度）
- 所有数据通过 `/api/risk-cases` 系列端点获取

**页面路由**：
- `/` → 风险看板（案件列表）
- `/cases/[id]` → 案件详情
- 审批通过抽屉/弹窗实现，不单独路由

### 决策 6：审批状态机

**选择**：线性状态流转 NEW → ANALYZED → PENDING_REVIEW → APPROVED/REJECTED

**原因**：
- MVP 阶段流程简洁明确
- 每次状态变更记录审计日志
- 原始 Agent 输出不可覆盖，审批结果新增版本

### 决策 7：图表库选择 Recharts

**选择**：Recharts（基于 React 的图表库）

**原因**：
- React 原生，与 Next.js 天然集成
- 声明式 API，开发效率高
- 满足趋势图和预测图需求

**备选方案**：
- ECharts → 功能更强大但需要额外封装 React 组件

## Risks / Trade-offs

- **[Mock Agent 与真实 LLM 差异]** → Mock 响应基于规则生成，无法完全模拟 LLM 行为。缓解：Mock 输出严格遵循 JSON Schema，确保接口一致性，未来替换只需改实现函数。

- **[SQLite 并发限制]** → SQLite 不支持高并发写入。缓解：MVP 阶段单用户/少量用户使用，性能不是瓶颈；SQLAlchemy 抽象层保证未来可无缝迁移到 PostgreSQL。

- **[14 日预测准确性]** → 滚动均值 + 季节性系数是简化模型，预测精度有限。缓解：标注置信度分数，让运营人员知晓预测可靠程度；后续可迭代为更复杂的模型。

- **[前后端跨域]** → 开发环境前端 3000 端口、后端 8000 端口需要处理 CORS。缓解：FastAPI 配置 CORSMiddleware 允许本地开发跨域。

- **[数据生成器与真实数据差距]** → Mock 数据无法完全反映真实业务复杂度。缓解：设计 3 类典型风险场景覆盖核心验收用例，数据模式尽量贴近真实分布。
