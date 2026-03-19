
# 🛡 商家经营保障 Agent / Merchant Business Protection Agent

![Version](https://img.shields.io/badge/version-3.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57)
![License](https://img.shields.io/badge/license-MIT-green)

> **面向内部运营人员的多 Agent 风控执行系统**
>
> A multi-agent risk-control execution system for internal operations teams.

将退货激增、现金缺口、疑似欺诈等风险信号转化为可追踪、可审批、可恢复的保障行动 —— 从发现异常到生成融资/理赔/复核草稿，全程由 9 个 Specialist Agent 协同完成，人类运营在关键节点审批把关。

Transform risk signals — surging returns, cash gaps, suspected fraud — into traceable, approvable, and resumable protection actions. From anomaly detection to financing/claim/review draft generation, 9 Specialist Agents collaborate end-to-end with human operators reviewing at critical checkpoints.

---

## 📑 目录 / Table of Contents

- [✨ 核心能力 / Features](#-核心能力--features)
- [🏗 系统架构 / Architecture](#-系统架构--architecture)
- [🚀 快速开始 / Quick Start](#-快速开始--quick-start)
- [📁 项目结构 / Project Structure](#-项目结构--project-structure)
- [🤖 Agent 架构 / Agent Architecture](#-agent-架构--agent-architecture)
- [🧠 LLM 接入设计 / LLM Integration](#-llm-接入设计--llm-integration)
- [🔌 API 参考 / API Reference](#-api-参考--api-reference)
- [🖥 界面预览 / Screenshots](#-界面预览--screenshots)
- [📊 数据模型 / Data Model](#-数据模型--data-model)
- [⚙️ 配置说明 / Configuration](#️-配置说明--configuration)
- [🧪 评测中心 / Evaluation](#-评测中心--evaluation)
- [📜 版本演进 / Changelog](#-版本演进--changelog)
- [🗺 路线图 / Roadmap](#-路线图--roadmap)
- [📄 许可证 / License](#-许可证--license)

---

## ✨ 核心能力 / Features

### 🤖 多 Agent 协同编排 / Multi-Agent Orchestration

使用 **LangGraph StateGraph** 编排 9 个 Specialist Agent，支持条件分支、错误路由和自动降级。

9 Specialist Agents orchestrated via **LangGraph StateGraph** with conditional branching, error routing, and automatic fallback.

### ⏸ 长流程可恢复工作流 / Durable Workflow Execution

工作流可跨分钟、小时甚至天级暂停和恢复。审批完成、外部回调返回或失败重试后，从断点继续执行。

Workflows can pause and resume across minutes, hours, or even days. Execution continues from the exact interruption point after approvals, external callbacks, or failure retries.

### ✅ 审批中心 + 守卫系统 / Approval Center + Guardrails

高风险动作（融资、理赔、反欺诈复核）默认进入审批队列。合规 Guard Agent 在执行前校验权限、schema、敏感词和额度阈值。

High-risk actions (financing, claims, fraud reviews) enter the approval queue by default. Compliance Guard Agent validates permissions, schema, sensitive terms, and threshold limits before execution.

### 📊 评测与观测 / Evaluation & Observability

离线评测集 + 线上抽样复核。追踪采纳率、幻觉率、证据覆盖率、schema 合格率。每次 agent run 记录完整轨迹。

Offline eval datasets + online sampling review. Track adoption rate, hallucination rate, evidence coverage, and schema pass rate. Every agent run is fully traced.

### 🔐 RBAC 权限 + 审计日志 / RBAC + Audit Trail

5 种角色（风险运营 / 融资运营 / 理赔运营 / 合规复核 / 管理员）× 细粒度权限矩阵。所有操作写入审计日志。

5 roles (Risk Ops / Finance Ops / Claim Ops / Compliance / Admin) × fine-grained permission matrix. All operations are audit-logged.

### 🔄 三级降级策略 / Three-Level Fallback Strategy

```
Agent 节点失败 / Agent Node Failure
     │
     ▼
L1: 自动重试 (max 3次, 指数退避)
    Auto Retry (max 3, exponential backoff)
     │ 失败 / Failed
     ▼
L2: 规则引擎降级 (evaluate_risk + generate_rule_recommendations)
    Rule Engine Fallback
     │ 失败 / Failed
     ▼
L3: 人工接管 (创建 ApprovalTask, workflow → PAUSED)
    Human Handoff (create ApprovalTask, workflow → PAUSED)
```

---

## 🏗 系统架构 / Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js 14 + Tailwind)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐  │
│  │风险指挥台│ │案件工作台│ │ 审批中心 │ │工作流   │ │设置/评测 │  │
│  │Dashboard │ │Case View │ │Approvals │ │Workflows│ │Settings  │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬────┘ └────┬─────┘  │
└───────┼────────────┼────────────┼─────────────┼───────────┼─────────┘
        │            │            │             │           │
        ▼            ▼            ▼             ▼           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (V3)                             │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  REST API    │  │ RBAC + Auth  │  │   Tool Registry          │  │
│  │  (46 routes) │  │ Middleware   │  │ (幂等 + 审批拦截)         │  │
│  └──────┬───────┘  └──────────────┘  └──────────────────────────┘  │
│         │                                                           │
│  ┌──────▼───────────────────────────────────────────────────────┐  │
│  │              LangGraph Workflow Engine                         │  │
│  │                                                               │  │
│  │  load_ctx → triage → metrics → forecast → evidence            │  │
│  │      → diagnose → recommend → guardrails                      │  │
│  │          → [approval] → execute → callback → summary          │  │
│  │                                                               │  │
│  │  ↕ Checkpoint (SQLite)   ↕ Pause/Resume   ↕ Retry/Fallback   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│  ┌──────▼──────┐  ┌────────────┐  ┌───────────┐  ┌─────────────┐  │
│  │  9 Agents   │  │Rule Engine │  │ Approval  │  │ Eval Center │  │
│  │  Specialist │  │Metrics/CF  │  │ Queue     │  │ Offline+    │  │
│  │             │  │            │  │           │  │ Sampling    │  │
│  └─────────────┘  └────────────┘  └───────────┘  └─────────────┘  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  SQLite DB  │
                    │ (25 tables) │
                    └─────────────┘
```

### 工作流状态机 / Workflow State Machine

```
NEW → TRIAGED → ANALYZING → RECOMMENDING → PENDING_APPROVAL → EXECUTING → COMPLETED
  │                │              │               │                │
  │                ▼              ▼               ▼                ▼
  │         NEEDS_MORE_DATA  BLOCKED_BY_GUARD  REJECTED    FAILED_RETRYABLE
  │                                                              │
  └───────────── ANY_STATE → PAUSED → RESUMED ◄─────────────────┘
```

---

## 🚀 快速开始 / Quick Start

### 环境要求 / Prerequisites

| 工具 / Tool | 版本 / Version |
|-------------|----------------|
| Python      | 3.11+          |
| Node.js     | 18+            |
| npm         | 9+             |

### 1️⃣ 克隆项目 / Clone

```bash
git clone <repo-url> m-agents
cd m-agents
```

### 2️⃣ 后端启动 / Backend Setup

```bash
# 创建虚拟环境 / Create virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖 / Install dependencies
pip install -r requirements.txt

# 初始化数据库 + 生成 Demo 数据 / Init DB + Generate demo data
python scripts/generate_mock_data.py --seed 42

# 启动后端服务 / Start backend server
uvicorn app.main:app --reload --port 8000
```

> 💡 **Demo 数据说明**: `generate_mock_data.py` 会生成 **50 个商家 × 90 天经营数据**，覆盖 3 类风险场景：
>
> | 场景 | 商家数 | 特征 |
> |------|--------|------|
> | **A: 高退货+回款延迟** | 10 | 退货率激增、现金缺口明显 |
> | **B: 高退货+现金充足** | 6 | 退货异常但无资金压力 |
> | **C: 异常退货模式** | 4 | 疑似欺诈退货特征 |
> | **N: 正常经营** | 30 | 基线对照组 |
>
> 同时自动生成工作流运行、审批任务、Prompt 版本、评测数据集等 V3 全量数据。使用 `--seed` 参数可复现相同数据。

### 3️⃣ 前端启动 / Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 4️⃣ 访问系统 / Access

| 服务 / Service      | 地址 / URL                             |
|---------------------|----------------------------------------|
| 前端 / Frontend     | http://localhost:3000                  |
| 后端 API / Backend  | http://localhost:8000                  |
| API 文档 / API Docs | http://localhost:8000/docs             |
| 健康检查 / Health   | http://localhost:8000/health           |

---

## 📁 项目结构 / Project Structure

```
m-agents/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI 入口 / Entry point
│   │   ├── agents/                    # 9 个 Specialist Agent
│   │   │   ├── orchestrator.py        # V1 编排器 (兼容模式)
│   │   │   ├── triage_agent.py        # A2 分诊 Agent
│   │   │   ├── analysis_agent.py      # A3 诊断 Agent
│   │   │   ├── recommend_agent.py     # A5 建议 Agent
│   │   │   ├── evidence_agent.py      # A6 证据 Agent
│   │   │   ├── compliance_agent.py    # A7 合规守卫 Agent
│   │   │   ├── execution_agent.py     # A8 执行 Agent
│   │   │   ├── summary_agent.py       # A9 总结 Agent
│   │   │   ├── guardrail.py           # 守卫规则引擎
│   │   │   └── schemas.py             # Agent 输入输出契约 (Pydantic)
│   │   ├── api/                       # REST API 路由层
│   │   │   ├── risk_cases.py          # 案件管理 API (V1/V2/V3)
│   │   │   ├── dashboard.py           # 风险指挥台 API
│   │   │   ├── tasks.py               # 任务管理 API (V2)
│   │   │   ├── workflows.py           # 工作流管理 API (V3)
│   │   │   ├── approvals.py           # 审批中心 API (V3)
│   │   │   ├── configs.py             # 配置管理 API (V3)
│   │   │   └── evals.py               # 评测中心 API (V3)
│   │   ├── workflow/                  # LangGraph 工作流引擎
│   │   │   ├── graph.py               # StateGraph 定义 + 条件路由
│   │   │   ├── nodes.py               # 14 个图节点实现
│   │   │   ├── state.py               # GraphState TypedDict 定义
│   │   │   └── retry.py               # 三级降级策略 (L1/L2/L3)
│   │   ├── engine/                    # 业务计算引擎 (非 LLM)
│   │   │   ├── metrics.py             # 商家指标计算
│   │   │   ├── cashflow.py            # 现金流预测
│   │   │   └── rules.py               # 规则引擎 + 降级建议
│   │   ├── core/                      # 基础设施
│   │   │   ├── config.py              # 全局配置 (Pydantic Settings)
│   │   │   ├── database.py            # SQLAlchemy 数据库连接
│   │   │   ├── auth_middleware.py      # 认证中间件
│   │   │   └── rbac.py                # 角色权限矩阵
│   │   ├── models/
│   │   │   └── models.py              # 25 张数据库表定义
│   │   ├── schemas/                   # Pydantic Request/Response
│   │   │   ├── schemas.py             # 通用 Schema
│   │   │   └── approval_schemas.py    # 审批 Schema
│   │   └── services/                  # 业务服务层
│   │       ├── approval.py            # 审批服务
│   │       ├── export.py              # 案件导出 (Markdown/JSON)
│   │       ├── risk_scanner.py        # 风险扫描器
│   │       ├── task_generator.py      # 任务自动生成
│   │       └── tool_registry.py       # 工具注册中心
│   ├── scripts/
│   │   ├── generate_mock_data.py      # Demo 数据生成 (50商家×90天)
│   │   ├── generate_risk_cases.py     # 风险案件生成
│   │   └── init_db.py                 # 数据库初始化
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx               # 风险指挥台 (Dashboard)
│   │   │   ├── layout.tsx             # 全局布局 + 导航
│   │   │   ├── cases/[id]/page.tsx    # 案件详情
│   │   │   ├── approvals/             # 审批中心
│   │   │   │   ├── page.tsx           # 审批列表
│   │   │   │   └── [id]/page.tsx      # 审批详情
│   │   │   ├── workflows/             # 工作流中心
│   │   │   │   ├── page.tsx           # 工作流列表
│   │   │   │   └── [id]/page.tsx      # 工作流详情 + 轨迹
│   │   │   ├── tasks/                 # 任务管理
│   │   │   │   ├── page.tsx           # 任务列表
│   │   │   │   ├── financing/[id]/    # 融资详情
│   │   │   │   ├── claims/[id]/       # 理赔详情
│   │   │   │   └── reviews/[id]/      # 复核详情
│   │   │   ├── evals/page.tsx         # 评测中心
│   │   │   └── settings/page.tsx      # 规则与模型设置
│   │   ├── lib/api.ts                 # API 客户端
│   │   └── types/index.ts             # TypeScript 类型定义
│   ├── package.json
│   ├── tailwind.config.ts
│   └── tsconfig.json
│
└── v3.md                              # V3 阶段详细 PRD
```

---

## 🤖 Agent 架构 / Agent Architecture

### Agent 列表 / Agent Registry

| Agent | 代号 | 当前实现 | 目标实现 | 职责 / Responsibility |
|-------|------|---------|---------|----------------------|
| **Monitor Agent** | A1 | 🟢 规则引擎 | 规则引擎 | 定时扫描异常商家，创建案件 |
| **Triage Agent** | A2 | 🟢 规则引擎 | Hybrid (规则+LLM) | 案件分类 + 优先级 + 路由决策 |
| **Diagnosis Agent** | A3 | 🟢 规则 + LLM | LLM (Structured Outputs) | 根因分析 + 业务可读解释 |
| **Forecast Agent** | A4 | 🟢 规则引擎 | 规则引擎 | 7/14/30 日现金流预测 |
| **Recommendation Agent** | A5 | 🟢 规则 + LLM | LLM (Structured Outputs) | 保障动作建议 + 收益预估 |
| **Evidence Agent** | A6 | 🟢 SQL 查询 | SQL + LLM 摘要 | 证据收集 + evidence bundle |
| **Compliance Guard** | A7 | 🟢 规则 + LLM | 规则 + LLM 语义检测 | 合规校验 + 审批拦截 |
| **Execution Agent** | A8 | 🟢 代码 | 代码 | 审批后执行连接器 |
| **Summary Agent** | A9 | 🟢 规则 + LLM | LLM (Structured Outputs) | 案件摘要生成 |

> 🟢 = 已完成（含 LLM 双路径支持） &nbsp;&nbsp; USE_LLM=true 时走 LLM，否则走规则引擎

### 工作流图节点 / Workflow Graph Nodes

```
load_case_context
       │
       ▼
  triage_case ──── (error) ──→ write_audit_log → END
       │
       ▼
 compute_metrics
       │
       ▼
  forecast_gap
       │
       ▼
collect_evidence
       │
       ▼
 diagnose_case
       │
       ▼
generate_recommendations
       │
       ▼
 run_guardrails ──┬── (blocked) ──→ write_audit_log → END
                  │
                  ├── (needs approval) ──→ create_approval_tasks
                  │                              │
                  │                              ▼
                  │                      wait_for_approval
                  │                         │         │
                  │                  (approved)    (rejected/pause)
                  │                         │         │
                  ▼                         ▼         ▼
            execute_actions  ◄──────────────┘     END / audit
                  │
                  ▼
       wait_external_callback
                  │
                  ▼
         finalize_summary
                  │
                  ▼
         write_audit_log → END
```

### 中断点 / Interrupt Points

以下节点支持 **暂停/恢复** (Pause / Resume)：

| 节点 | 触发条件 | 恢复方式 |
|------|---------|---------|
| `wait_for_approval` | 敏感动作需审批 | 审批中心通过/驳回 |
| `wait_external_callback` | 等待外部系统回调 | API 回调触发 |
| 任意节点 (失败后) | L3 人工接管 | 管理员手动恢复 |

---

## 🧠 LLM 接入设计 / LLM Integration

### 当前状态 / Current Status

当前所有 Agent 均以 **规则引擎 + 确定性代码** 实现（Mock 模式），无需任何 LLM API Key 即可完整运行全部功能。这是有意为之的设计：

All Agents currently run on **rule engines + deterministic code** (Mock mode) — no LLM API key is required. This is by design:

- ✅ 全部 14 个工作流节点可端到端运行
- ✅ 完整的输入/输出 Pydantic Schema 已定义
- ✅ 版本追踪基础设施就绪（`agent_runs` 表记录 `model_name`、`prompt_version`、`schema_version`）
- ✅ 评测中心可对比规则引擎 vs. LLM 输出质量
- ✅ 三级降级策略中 L2 = 规则引擎 fallback（即当前实现）

### 架构分层 / Architecture Layers

```
┌──────────────────────────────────────────────────────────────┐
│                    LangGraph Node (nodes.py)                  │
│   调用 Agent 函数，记录 agent_run，处理错误和降级              │
└──────────────┬───────────────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────────────┐
│                Agent 函数 (agents/*.py)                       │
│                                                              │
│   当前:  run_diagnosis(input, metrics, evidence)             │
│          → 规则引擎: if/else 条件 → DiagnosisOutput          │
│                                                              │
│   未来:  run_diagnosis(input, metrics, evidence)             │
│          → OpenAI Responses API + Structured Outputs         │
│          → 强制输出 DiagnosisOutput schema                   │
│          → 失败时 fallback 到规则引擎                         │
└──────────────┬───────────────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────────────┐
│              Pydantic Schema (agents/schemas.py)              │
│   AgentInput → DiagnosisOutput / RecommendationOutput / ...  │
│   LLM 和规则引擎共享同一套 Schema，输出格式完全一致            │
└──────────────────────────────────────────────────────────────┘
```

### LLM 接入计划 / Integration Plan

#### 目标模型 / Target Model

| 配置 | 值 | 说明 |
|------|---|------|
| Provider | OpenAI（或兼容 API） | Responses API (推荐) 或 Chat Completions API |
| Base URL | `https://api.openai.com/v1` | 支持自定义，可接入 Azure OpenAI / 私有化部署 / 兼容网关 |
| Model | `gpt-4o` | 推理 + Structured Outputs 兼备 |
| Output Mode | Structured Outputs | 保证输出严格遵守 Pydantic Schema |
| Fallback | 规则引擎 (当前实现) | LLM 调用失败时自动降级 |

#### 接入步骤 / Steps to Enable

```bash
# 1. 安装 OpenAI SDK
pip install openai

# 2. 配置环境变量
echo 'OPENAI_API_KEY=sk-...' >> backend/.env
echo 'OPENAI_BASE_URL=https://api.openai.com/v1' >> backend/.env  # 可选，默认 OpenAI 官方
echo 'OPENAI_MODEL=gpt-4o' >> backend/.env
echo 'USE_LLM=true' >> backend/.env

# 3. 无需修改工作流代码 — Agent 函数内部切换即可
```

> 💡 **自定义 Base URL**：如使用 Azure OpenAI、中转网关或私有化部署，只需修改 `OPENAI_BASE_URL` 即可，无需改动任何代码。

#### 需要接入 LLM 的 Agent / Agents Requiring LLM

| Agent | 当前输入 | LLM Prompt 核心职责 | Schema 约束 |
|-------|---------|--------------------|-----------|
| **Diagnosis (A3)** | metrics + evidence | 生成业务可读的根因解释文本 | `DiagnosisOutput` — root_causes[].explanation | ✅ 已接入 |
| **Recommendation (A5)** | metrics + forecast + evidence | 基于规则命中 + 业务上下文生成自然语言建议理由 | `RecommendationOutput` — recommendations[].why | ✅ 已接入 |
| **Summary (A9)** | 全部 Agent 输出 | 生成面向运营的案件摘要 | `SummaryOutput` — case_summary | ✅ 已接入 |
| **Compliance Guard (A7)** | recommendations 文本 | 语义级敏感内容检测（补充规则引擎） | `GuardOutput` — reason_codes | ✅ 已接入 |

#### 切换机制 / Switching Mechanism

```python
# agents/analysis_agent.py 中的切换示例
def run_diagnosis(agent_input, metrics, evidence) -> DiagnosisOutput:
    if settings.USE_LLM and settings.OPENAI_API_KEY:
        try:
            return _llm_diagnosis(agent_input, metrics, evidence)  # LLM 模式
        except Exception:
            pass  # fallback 到规则引擎
    return _rule_diagnosis(agent_input, metrics, evidence)  # 当前规则实现
```

#### Prompt 版本管理 / Prompt Versioning

系统已内置 Prompt 版本管理基础设施：

- `prompt_versions` 表：存储每个 Agent 的 Prompt 内容 + 版本号 + 状态
- **灰度权重** (`canary_weight`)：新版本可按比例分流，例如 10% 流量走新 Prompt
- `agent_runs` 表：每次调用记录 `prompt_version`，可回溯到使用了哪个版本
- API 支持激活 (`/activate`) 和回滚 (`/rollback`) Prompt 版本

#### 不使用 LLM 的 Agent / Rule-Only Agents

| Agent | 原因 |
|-------|------|
| **Monitor (A1)** | 纯指标阈值扫描，确定性逻辑，无需 LLM |
| **Triage (A2)** | 基于指标的条件分支路由，可预测性优先 |
| **Forecast (A4)** | 现金流预测为数值计算，LLM 不适合数值推理 |
| **Execution (A8)** | 连接器调用，纯代码执行 |

> 💡 **设计原则**：遵循 V3 PRD 原则 1 —「代码主导流程，LLM 只在边界内工作」。数值计算、状态流转、工具调用由代码控制；LLM 仅负责自然语言理解与生成，且输出必须通过 Structured Outputs 钉死在 Schema 上。

---

## 🔌 API 参考 / API Reference

### 案件管理 / Case Management

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/risk-cases` | 案件列表（支持筛选、排序、分页） |
| `GET` | `/api/risk-cases/{id}` | 案件详情（含指标、预测、证据、建议、审批记录） |
| `POST` | `/api/risk-cases/{id}/analyze?mode=v3` | 触发分析（支持 V1 / V3 模式切换） |
| `GET` | `/api/risk-cases/{id}/evidence` | 证据列表 |
| `POST` | `/api/risk-cases/{id}/review` | 案件审批 |
| `GET` | `/api/risk-cases/{id}/export?format=markdown` | 导出案件（Markdown / JSON） |
| `GET` | `/api/risk-cases/{id}/tasks` | 案件关联任务 |
| `POST` | `/api/risk-cases/{id}/generate-financing-application` | 手动触发融资申请 |
| `POST` | `/api/risk-cases/{id}/generate-claim-application` | 手动触发理赔申请 |
| `POST` | `/api/risk-cases/{id}/generate-manual-review` | 手动触发复核任务 |

### 风险指挥台 / Dashboard

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/dashboard/stats` | 看板统计（商家数、高风险案件、现金缺口、回款延迟） |

### 工作流引擎 / Workflow Engine

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/workflows` | 工作流列表（支持状态/案件筛选） |
| `GET` | `/api/workflows/{id}` | 工作流详情（含 Agent Run 列表） |
| `GET` | `/api/workflows/{id}/trace` | 执行轨迹（节点级耗时 + 输入输出） |
| `POST` | `/api/workflows/start` | 启动工作流 |
| `POST` | `/api/workflows/{id}/resume` | 恢复暂停的工作流 |
| `POST` | `/api/workflows/{id}/retry` | 重试失败的工作流 |
| `GET` | `/api/cases/{id}/latest-run` | 获取案件最新工作流 |
| `POST` | `/api/cases/{id}/reopen` | 重开案件（创建新 workflow_run） |

### 审批中心 / Approval Center

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/approvals` | 审批列表（支持状态/类型筛选 + SLA 超时检测） |
| `GET` | `/api/approvals/{id}` | 审批详情 |
| `POST` | `/api/approvals/{id}/approve` | 批准 |
| `POST` | `/api/approvals/{id}/reject` | 驳回 |
| `POST` | `/api/approvals/{id}/revise-and-approve` | 修改后批准 |
| `POST` | `/api/approvals/batch` | 批量审批 |

### 配置管理 / Configuration Management

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/agent-configs` | 获取所有 Agent 配置 |
| `GET` | `/api/prompt-versions` | Prompt 版本列表 |
| `POST` | `/api/prompt-versions` | 创建 Prompt 版本 |
| `POST` | `/api/prompt-versions/{id}/activate` | 激活版本 |
| `POST` | `/api/prompt-versions/{id}/rollback` | 回滚版本 |
| `POST` | `/api/schema-versions` | 创建 Schema 版本 |
| `POST` | `/api/model-policies` | 创建/更新模型策略 |

### 评测中心 / Evaluation Center

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/evals/datasets` | 评测数据集列表 |
| `POST` | `/api/evals/datasets` | 创建评测数据集 |
| `GET` | `/api/evals/runs` | 评测运行列表 |
| `POST` | `/api/evals/runs` | 启动评测运行 |
| `GET` | `/api/evals/runs/{id}` | 评测结果详情 |
| `GET` | `/api/evals/sampling` | 线上抽样 |

### 任务管理 / Task Management

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/tasks` | 统一任务列表（融资/理赔/复核） |
| `GET` | `/api/tasks/{type}/{id}` | 任务详情 |
| `PUT` | `/api/tasks/{type}/{id}/status` | 任务状态更新（含状态机校验） |

### 系统 / System

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查 |

---

## 🖥 界面预览 / Screenshots

> 📸 *Screenshots coming soon / 截图待补充*

| 页面 | 描述 |
|------|------|
| 风险指挥台 | 商家热力列表 + 趋势图 + 统计卡片 |
| 案件详情 | 商家画像 + 风险评分 + 现金流预测 + Agent 总结 + 建议 + 证据链 |
| 审批中心 | 待审批列表 + SLA 倒计时 + 一键批准/驳回/修改后批准 |
| 工作流中心 | workflow_run 列表 + 节点状态图 + 耗时 + 失败回溯 |
| 评测中心 | 评测集管理 + 运行结果 + 指标可视化 |
| 设置页面 | Prompt 版本 + Schema 版本 + 模型策略 |

---

## 📊 数据模型 / Data Model

系统共 **25 张数据库表**，完整 ER 图和字段说明请查看 👉 [docs/data-model.md](docs/data-model.md)

### 表概览 / Table Overview

#### V1/V2 核心业务表

| # | 表名 | 说明 |
|---|------|------|
| 1 | `merchants` | 商家基础信息 |
| 2 | `orders` | 订单 |
| 3 | `returns` | 退货退款 |
| 4 | `logistics_events` | 物流事件 |
| 5 | `settlements` | 结算回款 |
| 6 | `insurance_policies` | 保险保单 |
| 7 | `financing_products` | 融资产品 |
| 8 | `risk_cases` | 风险案件 |
| 9 | `evidence_items` | 证据项 |
| 10 | `recommendations` | 建议 |
| 11 | `reviews` | 案件审批记录 |
| 12 | `audit_logs` | 审计日志 |
| 13 | `financing_applications` | 融资申请 |
| 14 | `claims` | 理赔申请 |
| 15 | `manual_reviews` | 人工复核任务 |

#### V3 多 Agent 生产化表

| # | 表名 | 说明 |
|---|------|------|
| 16 | `workflow_runs` | 工作流运行实例 |
| 17 | `agent_runs` | Agent 运行记录（含版本追踪） |
| 18 | `checkpoints` | 工作流断点 |
| 19 | `approval_tasks` | 审批任务队列 |
| 20 | `tool_invocations` | 工具调用日志（含幂等键） |
| 21 | `prompt_versions` | Prompt 版本管理（含灰度权重） |
| 22 | `schema_versions` | Schema 版本管理 |
| 23 | `eval_datasets` | 评测数据集 |
| 24 | `eval_runs` | 评测运行 |
| 25 | `eval_results` | 评测结果 |

---

## ⚙️ 配置说明 / Configuration

### 环境变量 / Environment Variables

在 `backend/` 目录下创建 `.env` 文件 / Create `.env` file in `backend/`:

```env
# 数据库（默认 SQLite）/ Database (default SQLite)
DATABASE_URL=sqlite:///data.db

# CORS 允许的来源 / Allowed CORS origins
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]

# LLM 配置（可选，不配置则使用规则引擎模式）/ LLM Config (optional, rule engine by default)
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1    # 支持 Azure OpenAI / 私有化部署 / 兼容网关
OPENAI_MODEL=gpt-4o
USE_LLM=true
```

### 风险阈值 / Risk Thresholds

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `RETURN_RATE_AMPLIFICATION_THRESHOLD` | 1.6 | 退货率放大倍数阈值 |
| `PREDICTED_GAP_THRESHOLD` | 50000.0 | 预测现金缺口阈值 (元) |
| `SETTLEMENT_DELAY_THRESHOLD` | 3.0 | 回款延迟天数阈值 |
| `ANOMALY_SCORE_THRESHOLD` | 0.8 | 异常分数阈值 |
| `HIGH_RISK_AMPLIFICATION` | 1.6 | 高风险退货放大倍数 |
| `HIGH_RISK_GAP` | 50000.0 | 高风险现金缺口 (元) |
| `HIGH_RISK_ANOMALY` | 0.8 | 高风险异常分数 |
| `MEDIUM_RISK_AMPLIFICATION` | 1.3 | 中风险退货放大倍数 |
| `MEDIUM_RISK_DELAY` | 2.0 | 中风险回款延迟天数 |

### RBAC 角色 / Roles

| 角色 | 代号 | 核心权限 |
|------|------|---------|
| 风险运营 | `risk_ops` | 查看案件、触发分析、审批反欺诈复核 |
| 融资运营 | `finance_ops` | 审批融资、修改建议 |
| 理赔运营 | `claim_ops` | 审批理赔、修改建议 |
| 合规复核 | `compliance` | 查看审计、拒绝高风险建议 |
| 管理员 | `admin` | 全部权限（含配置管理、评测管理） |

> 💡 开发阶段默认以 `admin` 角色登录，可通过 HTTP Header `X-User-Role` 切换角色。

---

## 🧪 评测中心 / Evaluation

### 离线评测 / Offline Evaluation

```bash
# 通过 API 创建评测数据集
curl -X POST http://localhost:8000/api/evals/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "v3-baseline",
    "description": "V3 基线评测集",
    "test_cases": [
      {"input": {"merchant_id": 1}, "expected_output": {"risk_level": "high"}}
    ]
  }'

# 启动评测运行
curl -X POST http://localhost:8000/api/evals/runs \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": 1, "model_name": "gpt-4o", "prompt_version": "1"}'
```

### 评测指标 / Evaluation Metrics

| 指标 | 说明 | 目标 |
|------|------|------|
| 采纳率 (Adoption Rate) | 建议被运营采纳的比例 | > 60% |
| 幻觉率 (Hallucination Rate) | 无证据支撑的输出比例 | 越低越好 |
| 证据覆盖率 (Evidence Coverage) | 建议有 evidence_ids 绑定的比例 | > 95% |
| Schema 合格率 (Schema Pass Rate) | 输出符合 schema 的比例 | > 99% |
| 审批驳回率 (Rejection Rate) | 建议被审批驳回的比例 | 持续下降 |

### 线上抽样 / Online Sampling

```bash
# 从线上 agent_runs 中随机抽样
curl "http://localhost:8000/api/evals/sampling?agent_name=recommendation_agent&sample_size=10"
```

---

## 📜 版本演进 / Changelog

```
V1 (MVP)                       V2 (闭环执行)                   V3 (多Agent生产化)
─────────────────►──────────────────────────►──────────────────────────────►
• 风险案件分析                  • 融资/理赔/复核任务             • LangGraph 9-Agent 编排
• 3 Agent 编排                  • 执行闭环                       • 审批门禁 + 守卫系统
• 规则引擎 + 指标计算           • 任务状态机                     • Checkpoint 持久化
• 案件列表 / 详情               • 审批服务                       • 三级降级 (L1/L2/L3)
• 证据链                        • 导出报告                       • RBAC 5 角色权限
                                                                 • 评测中心 (离线+抽样)
                                                                 • Prompt/Schema 版本管理
                                                                 • 灰度开关
                                                                 • 工具注册中心 (幂等+审批)
                                                                 • 46 API 端点
```

---

## 🗺 路线图 / Roadmap

- [x] 🔌 接入真实 LLM (OpenAI Responses API / Structured Outputs) — A3/A5/A7/A9 已完成
- [ ] 🗄 迁移 PostgreSQL 生产数据库
- [ ] 📡 WebSocket 实时工作流进度推送
- [ ] 📈 可观测面板 (Prometheus + Grafana)
- [ ] 🔒 OAuth 2.0 / SSO 集成
- [ ] 🧪 端到端评测流水线 (CI/CD)
- [ ] 🌐 多租户隔离
- [ ] 📱 移动端审批
- [ ] 🤖 接入 OpenAI Agents SDK Guardrails

---

## 📄 许可证 / License

本项目采用 [MIT License](LICENSE) 开源协议。

This project is licensed under the [MIT License](LICENSE).
