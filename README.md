# 🛡 商家经营保障 Agent / Merchant Business Protection Agent

![Version](https://img.shields.io/badge/version-5.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1)
![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5-FF6F00)
![JWT](https://img.shields.io/badge/Auth-JWT-orange)
![License](https://img.shields.io/badge/license-MIT-green)

> **面向内部运营人员的多 Agent 风控执行系统**
>
> A multi-agent risk-control execution system for internal operations teams.

将退货激增、现金缺口、疑似欺诈等风险信号转化为可追踪、可审批、可恢复的保障行动 —— 从发现异常到生成融资/理赔/复核草稿，全程由 9 个 Specialist Agent 协同完成，人类运营在关键节点审批把关。支持 **RAG 对话式分析**、**LLM Agent 智能增强**、**实时工作流可视化** 和 **LLM-as-Judge 评测**。

Transform risk signals — surging returns, cash gaps, suspected fraud — into traceable, approvable, and resumable protection actions. From anomaly detection to financing/claim/review draft generation, 9 Specialist Agents collaborate end-to-end with human operators reviewing at critical checkpoints. Features **RAG-powered conversational analysis**, **hybrid LLM-enhanced Agents**, **real-time workflow visualization**, and **LLM-as-Judge evaluation**.

---

## 📑 目录 / Table of Contents

- [✨ 核心能力 / Features](#-核心能力--features)
- [📸 系统截图 / Screenshots](#-系统截图--screenshots)
- [🏗 系统架构 / Architecture](#-系统架构--architecture)
- [🚀 快速开始 / Quick Start](#-快速开始--quick-start)
- [📁 项目结构 / Project Structure](#-项目结构--project-structure)
- [🤖 Agent 架构 / Agent Architecture](#-agent-架构--agent-architecture)
- [🧠 LLM 接入设计 / LLM Integration](#-llm-接入设计--llm-integration)
- [💬 RAG 对话系统 / RAG Conversation](#-rag-对话系统--rag-conversation)
- [🔐 认证与用户管理 / Authentication](#-认证与用户管理--authentication)
- [🔌 API 参考 / API Reference](#-api-参考--api-reference)
- [📊 数据模型 / Data Model](#-数据模型--data-model)
- [⚙️ 配置说明 / Configuration](#️-配置说明--configuration)
- [🧪 评测中心 / Evaluation](#-评测中心--evaluation)
- [📡 可观测面板 / Observability](#-可观测面板--observability)
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

### 💬 RAG 对话式分析 / RAG Conversational Analysis

案件详情页内置**对话面板**，运营人员可基于案件分析结果与 Agent 多轮对话追问。底层使用 **ChromaDB 向量数据库**进行语义检索，将案件证据、Agent 输出、商家信息向量化索引，实现 RAG 增强的精准回答。

Built-in **conversation panel** on case detail page. Operators can engage in multi-turn dialogue with Agents based on analysis results. Powered by **ChromaDB vector database** for semantic retrieval, with case evidence, Agent outputs, and merchant data vectorized for RAG-enhanced precise answers.

### 🧠 Agent 智能增强 / Agent Intelligence Enhancement

Triage Agent 升级为 **Hybrid 架构**（规则预过滤 + LLM 精细分类），Evidence Agent 新增 **LLM 分析层**（动态评分 + 关联模式发现），全链路 `analysis_context` **累积式上下文传递**，4 个 LLM Agent 使用**专家级 Prompt 框架**（CoT + Few-Shot + 反面约束）。

Triage Agent upgraded to **Hybrid architecture** (rule pre-filter + LLM fine classification), Evidence Agent with **LLM analysis layer** (dynamic scoring + pattern discovery), full-chain `analysis_context` **cumulative context passing**, 4 LLM Agents using **expert-level Prompt framework** (CoT + Few-Shot + negative constraints).

### 📡 实时工作流可视化 / Real-time Workflow Visualization

分析过程通过 **SSE 流式推送**实时展示 Agent 工作流各阶段进度、状态和耗时。LLM Agent 节点可展开查看输入 Prompt 和大模型流式回复（打字机效果）。重新分析自动清理旧数据，保证结果干净。

Analysis progress streamed in real-time via **SSE** showing each Agent workflow stage's progress, status, and latency. LLM Agent nodes expandable to view input prompts and streaming model responses (typewriter effect). Re-analysis auto-cleans old data for fresh results.

### 📊 评测与观测 / Evaluation & Observability

**真实 Agent 工作流评测**替代 mock 实现，引入 **LLM-as-Judge** 语义级质量评分。**可观测面板**可视化展示 Agent 运行指标、趋势分析和性能监控。离线评测集 + 线上抽样复核，追踪采纳率、幻觉率、证据覆盖率、schema 合格率。

**Real Agent workflow evaluation** replacing mock implementation, introducing **LLM-as-Judge** semantic quality scoring. **Observability dashboard** visualizes Agent runtime metrics, trend analysis, and performance monitoring. Offline eval datasets + online sampling review.

### 🔐 RBAC 权限 + 审计日志 / RBAC + Audit Trail

5 种角色（风险运营 / 融资运营 / 理赔运营 / 合规复核 / 管理员）× 细粒度权限矩阵。所有操作写入审计日志。

5 roles (Risk Ops / Finance Ops / Claim Ops / Compliance / Admin) × fine-grained permission matrix. All operations are audit-logged.

### 🔑 JWT 认证 + 用户管理 / JWT Auth + User Management

系统内置完整的认证体系：首次启动引导式创建超级管理员、JWT Access/Refresh Token 双令牌机制、管理员注册新用户、修改密码、启用/禁用账号、角色管理。前端自动处理 Token 刷新与过期跳转。

Built-in authentication: guided super-admin setup on first launch, JWT Access/Refresh dual-token mechanism, admin-managed user registration, password management, account enable/disable, and role assignment. Frontend handles token refresh and expiry redirects automatically.

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

## 📸 系统截图 / Screenshots

### 风险控制台 / Risk Dashboard

运营人员的主工作台，展示商家风险全景：高风险案件数、现金缺口总额、待处理审批等核心指标一目了然。

The main workspace for operators, showing a panoramic view of merchant risks: high-risk cases, total cash gaps, pending approvals, and other key metrics at a glance.

![风险控制台](docs/picture/风险控制台.png)

### 案件详情 / Case Detail

单个案件的完整分析视图，包含商家信息、风险指标、证据链、处置建议，以及右侧的 RAG 对话面板支持自然语言追问。

Complete analysis view for a single case, including merchant info, risk metrics, evidence chain, recommendations, and a RAG conversation panel on the right for natural language follow-up questions.

![案件详情](docs/picture/案件详情.png)

### Agent 工作流可视化 / Agent Workflow Visualization

实时展示 9 个 Agent 的工作流执行进度，每个节点的状态、耗时一目了然。LLM Agent 节点可展开查看输入 Prompt 和流式回复。

Real-time visualization of the 9-Agent workflow execution progress, with each node's status and latency clearly displayed. LLM Agent nodes can be expanded to view input prompts and streaming responses.

![Agent工作流](docs/picture/agent工作流.png)

### 工作流中心 / Workflow Center

所有工作流运行实例的管理视图，支持按状态筛选、查看执行轨迹、重试失败的工作流。

Management view for all workflow run instances, supporting status filtering, execution trace viewing, and retrying failed workflows.

![工作流中心](docs/picture/工作流中心.png)

### 审批中心 / Approval Center

高风险动作的审批队列，融资、理赔、反欺诈复核等审批任务集中管理，支持批量审批和 SLA 超时检测。

Approval queue for high-risk actions, centrally managing financing, claims, and fraud review approvals, with batch approval and SLA timeout detection.

![审批中心](docs/picture/审批中心.png)

### 审批详情 / Approval Detail

单个审批任务的详细信息，包含 Agent 生成的处置建议、风险评估依据，审批人可批准、驳回或修改后批准。

Detailed view of a single approval task, including Agent-generated recommendations and risk assessment basis. Approvers can approve, reject, or revise-and-approve.

![审批详情](docs/picture/审批详情.png)

### 评测中心 / Evaluation Center

LLM-as-Judge 评测中心，展示评测运行列表、数据集管理，支持对比不同 Prompt 版本和模型的分析质量。

LLM-as-Judge evaluation center, showing evaluation run lists and dataset management, supporting quality comparison across different Prompt versions and models.

![评测中心](docs/picture/评测中心.png)

### 评测详情 / Evaluation Detail

单次评测运行的详细结果，包含每条测试用例的 LLM-Judge 评分、幻觉检测、证据覆盖率等质量指标。

Detailed results of a single evaluation run, including LLM-Judge scores, hallucination detection, and evidence coverage metrics for each test case.

![评测详情](docs/picture/评测详情.png)

### 可观测面板 / Observability Dashboard

Agent 运行可观测面板，可视化展示今日分析量、平均响应时间、LLM 调用成功率、降级触发次数，以及近 7 天趋势图表。

Agent runtime observability dashboard, visualizing today's analysis volume, average response time, LLM call success rate, fallback trigger count, and 7-day trend charts.

![可观测面板](docs/picture/可观测.png)

### 设置 / Settings

系统配置页面，包含规则引擎阈值配置、Agent 配置管理、Prompt 版本管理（支持灰度分流和版本回滚）。

System configuration page, including rule engine threshold settings, Agent configuration management, and Prompt version management (with canary deployment and version rollback).

![设置](docs/picture/设置.png)

---

## 🏗 系统架构 / Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js 14 + Tailwind)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐  │
│  │风险指挥台│ │案件工作台│ │ 审批中心 │ │工作流   │ │设置/评测 │  │
│  │Dashboard │ │Case View │ │Approvals │ │Workflows│ │Settings  │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬────┘ └────┬─────┘  │
│       │            │            │             │           │         │
│  ┌────▼────────────▼────────────▼─────────────▼───────────▼─────┐  │
│  │              AuthProvider (JWT Token 管理)                    │  │
│  │         自动刷新 / 过期跳转 / 登录状态维护                     │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
└─────────────────────────────┼───────────────────────────────────────┘
                              │ HTTP + Bearer Token
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (V5.0)                           │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  REST API    │  │ JWT Auth +   │  │   Tool Registry          │  │
│  │  (60+ routes)│  │ RBAC 中间件  │  │ (幂等 + 审批拦截)         │  │
│  └──────┬───────┘  └──────────────┘  └──────────────────────────┘  │
│         │                                                           │
│  ┌──────▼───────────────────────────────────────────────────────┐  │
│  │              LangGraph Workflow Engine                         │  │
│  │                                                               │  │
│  │  load_ctx → triage → metrics → forecast → evidence            │  │
│  │      → diagnose → recommend → guardrails                      │  │
│  │          → [approval] → execute → callback → summary          │  │
│  │                                                               │  │
│  │  ↕ Checkpoint (MySQL)   ↕ Pause/Resume   ↕ Retry/Fallback    │  │
│  └───────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│  ┌──────▼──────┐  ┌────────────┐  ┌───────────┐  ┌─────────────┐  │
│  │  9 Agents   │  │Rule Engine │  │ Approval  │  │ Eval Center │  │
│  │  Specialist │  │Metrics/CF  │  │ Queue     │  │ LLM-Judge   │  │
│  │  (Hybrid)   │  │            │  │           │  │ + Sampling  │  │
│  └─────────────┘  └────────────┘  └───────────┘  └─────────────┘  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
               ┌───────────┼───────────┐
               │           │           │
        ┌──────▼──────┐    │    ┌──────▼──────┐
        │  MySQL 8.0  │    │    │  通义千问    │
        │ (28 tables) │    │    │  qwen-plus  │
        └─────────────┘    │    └─────────────┘
                           │
               ┌───────────┼───────────┐
               │                       │
        ┌──────▼──────┐         ┌──────▼──────┐
        │ LLM Gateway │         │  ChromaDB   │
        │ (DashScope) │         │ (向量检索)   │
        └─────────────┘         └─────────────┘
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
| Python      | 3.10+          |
| Node.js     | 18+            |
| npm         | 9+             |
| MySQL       | 8.0+           |

### 1️⃣ 克隆项目 / Clone

```bash
git clone <repo-url> m-agents
cd m-agents
```

### 2️⃣ 数据库准备 / Database Setup

```bash
# 创建 MySQL 数据库 / Create MySQL database
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS m_agents CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 3️⃣ 后端启动 / Backend Setup

```bash
# 创建虚拟环境 / Create virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖 / Install dependencies
pip install -r requirements.txt

# 配置环境变量 / Configure environment
cp .env.example .env  # 根据实际情况修改 .env 中的配置
# 或手动创建 .env 文件，至少配置 JWT_SECRET_KEY（见配置说明章节）

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

### 4️⃣ 前端启动 / Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 5️⃣ 首次使用 / First Launch

首次访问系统时，会自动进入**系统初始化**页面，引导创建超级管理员账号：

1. 打开 `http://localhost:3000`
2. 系统检测到无用户，自动显示初始化引导
3. 设置超级管理员的用户名、显示名称和密码
4. 完成后自动登录，进入风险指挥台

> ⚠️ **安全提示**：首个超级管理员创建后，`/api/auth/setup` 接口自动关闭，无法再次调用。

### 6️⃣ 访问系统 / Access

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
│   │   │   ├── risk_cases.py          # 案件管理 API (V1/V2/V3 + SSE 流式分析)
│   │   │   ├── dashboard.py           # 风险指挥台 API
│   │   │   ├── tasks.py               # 任务管理 API (V2)
│   │   │   ├── workflows.py           # 工作流管理 API (V3)
│   │   │   ├── approvals.py           # 审批中心 API (V3)
│   │   │   ├── configs.py             # 配置管理 API (V3)
│   │   │   ├── evals.py               # 评测中心 API (含 LLM-Judge)
│   │   │   ├── conversations.py       # 对话式分析 API (RAG + SSE 流式)
│   │   │   ├── observability.py       # 可观测面板 API (Agent 运行统计)
│   │   │   ├── auth.py                # 认证 API (登录/注册/Token/初始化)
│   │   │   └── users.py               # 用户管理 API (CRUD)
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
│   │   │   ├── database.py            # SQLAlchemy 数据库连接 (MySQL)
│   │   │   ├── security.py            # 密码哈希 + JWT Token 管理
│   │   │   ├── auth_middleware.py      # JWT 认证 + 权限校验中间件
│   │   │   ├── rbac.py                # 角色权限矩阵
│   │   │   ├── llm_client.py          # LLM 客户端 (普通+流式调用, 超时保护)
│   │   │   ├── vector_store.py        # ChromaDB 向量存储封装 (RAG 检索)
│   │   │   ├── prompt_loader.py       # Prompt 版本运行时加载器 (灰度分流)
│   │   │   ├── logging_config.py      # loguru 统一日志配置
│   │   │   ├── exceptions.py          # 全局异常类定义
│   │   │   ├── error_codes.py         # 标准化错误码
│   │   │   └── utils.py               # 通用工具函数
│   │   ├── models/
│   │   │   └── models.py              # 28 张数据库表定义
│   │   ├── schemas/                   # Pydantic Request/Response
│   │   │   ├── schemas.py             # 通用 Schema
│   │   │   ├── approval_schemas.py    # 审批 Schema
│   │   │   └── auth_schemas.py        # 认证与用户 Schema
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
│   │   │   ├── layout.tsx             # 全局布局 + 侧边导航
│   │   │   ├── error.tsx              # 全局错误边界
│   │   │   ├── login/page.tsx         # 登录页面
│   │   │   ├── cases/[id]/page.tsx    # 案件详情 (含对话面板+工作流面板)
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
│   │   │   ├── evals/                 # 评测中心
│   │   │   │   ├── page.tsx           # 评测列表
│   │   │   │   └── [runId]/page.tsx   # 评测结果详情
│   │   │   ├── observability/page.tsx # 可观测面板
│   │   │   └── settings/page.tsx      # 规则与模型设置
│   │   ├── lib/
│   │   │   ├── api.ts                 # API 客户端
│   │   │   ├── auth.tsx               # AuthProvider (JWT Token 管理 + 登录/注销)
│   │   │   ├── sse.ts                 # SSE 流式通信辅助函数
│   │   │   └── constants.ts           # 状态/名称中文映射 + 常量
│   │   └── types/index.ts             # TypeScript 类型定义
│   ├── package.json
│   ├── tailwind.config.ts
│   └── tsconfig.json
│
├── openspec/                          # 变更规范与设计文档
│   └── changes/
│       ├── merchant-risk-agent-mvp/   # V1 MVP 核心系统
│       ├── v2-closed-loop-execution/  # V2 执行闭环
│       ├── v3-multi-agent-production/ # V3 多 Agent 生产化
│       ├── admin-auth-management/     # V3.1 认证系统
│       ├── premium-frontend-redesign/ # 前端视觉重构
│       ├── chinese-status-and-agent-names/ # 中文状态映射
│       ├── analysis-workflow-display/ # 分析工作流可视化
│       ├── llm-agent-io-display/      # LLM IO 展示
│       ├── engineering-robustness/    # 工程健壮性 V1
│       ├── engineering-robustness-v2/ # 工程健壮性 V2 (MySQL+安全)
│       ├── conversational-analysis/   # 对话式分析+可观测
│       ├── ui-polish/                 # UI 打磨
│       ├── real-eval-center/          # 真实评测中心
│       └── agent-intelligence-enhancement/ # Agent 智能增强
│
└── v3.md                              # V3 阶段详细 PRD
```

---

## 🤖 Agent 架构 / Agent Architecture

### Agent 列表 / Agent Registry

| Agent | 代号 | 当前实现 | 架构模式 | 职责 / Responsibility |
|-------|------|---------|---------|----------------------|
| **Monitor Agent** | A1 | 🟢 规则引擎 | 纯规则 | 定时扫描异常商家，创建案件 |
| **Triage Agent** | A2 | 🟢 Hybrid (规则+LLM) | 三级决策 | 确定区间规则判定 + 模糊区间 LLM 精细分类 + 安全网后处理 |
| **Diagnosis Agent** | A3 | 🟢 LLM (Expert Prompt) | Structured Outputs | 根因分析 + 业务可读解释 (CoT 推理链) |
| **Forecast Agent** | A4 | 🟢 规则引擎 | 纯规则 | 7/14/30 日现金流预测 |
| **Recommendation Agent** | A5 | 🟢 LLM (Expert Prompt) | Structured Outputs | 保障动作建议 + 收益预估 (CoT 推理链) |
| **Evidence Agent** | A6 | 🟢 SQL + LLM 分析 | 两阶段 | SQL 证据收集 + LLM 动态评分/关联分析/洞察摘要 |
| **Compliance Guard** | A7 | 🟢 规则 + LLM (Expert Prompt) | 规则 + 语义检测 | 合规校验 + 审批拦截 (CoT 推理链) |
| **Execution Agent** | A8 | 🟢 代码 | 纯代码 | 审批后执行连接器 |
| **Summary Agent** | A9 | 🟢 LLM (Expert Prompt) | Structured Outputs | 案件摘要生成 (CoT 推理链) |

> 🟢 = 已完成（含 LLM 双路径支持） &nbsp;&nbsp; USE_LLM=true 时走 LLM，否则走规则引擎
> 🧠 Agent 间通过 `analysis_context` 累积字段传递全链路推理上下文
> 📝 Prompt 运行时从 DB 加载，支持灰度分流和版本回滚

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

系统默认接入**通义千问 (qwen-plus)**，通过 DashScope OpenAI 兼容 API 调用。所有 Agent 均支持 **LLM 模式** 和 **规则引擎模式** 双路径：`USE_LLM=true` 时走 LLM，否则走规则引擎。

The system integrates **Tongyi Qianwen (qwen-plus)** by default via DashScope's OpenAI-compatible API. All Agents support dual paths: **LLM mode** and **rule engine mode** — controlled by `USE_LLM=true`.

- ✅ 全部 14 个工作流节点可端到端运行
- ✅ 完整的输入/输出 Pydantic Schema 已定义
- ✅ A2 (Triage) Hybrid 架构（规则+LLM）已接入
- ✅ A3 (诊断) / A5 (建议) / A7 (合规) / A9 (总结) Expert Prompt 已接入
- ✅ A6 (证据) SQL + LLM 分析层已接入
- ✅ Agent 间 `analysis_context` 累积式上下文传递
- ✅ PromptLoader 运行时从 DB 加载 Prompt，支持灰度分流
- ✅ 版本追踪基础设施就绪（`agent_runs` 表记录 `model_name`、`prompt_version`、`schema_version`）
- ✅ 评测中心可对比规则引擎 vs. LLM 输出质量
- ✅ 三级降级策略中 L2 = 规则引擎 fallback
- ✅ LLM 调用超时保护（连接 10s / 读取 60s）

### 架构分层 / Architecture Layers

```
┌──────────────────────────────────────────────────────────────┐
│                    LangGraph Node (nodes.py)                  │
│   调用 Agent 函数，记录 agent_run，处理错误和降级              │
│   通过 analysis_context 累积传递全链路推理上下文              │
└──────────────┬───────────────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────────────┐
│                Agent 函数 (agents/*.py)                       │
│                                                              │
│   PromptLoader 从 DB 加载当前 ACTIVE 版本 Prompt               │
│   → canary_weight 灰度分流                                    │
│   → OpenAI Structured Outputs + Expert Prompt (CoT)          │
│   → 失败时 fallback 到规则引擎                                 │
└──────────────┬───────────────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────────────┐
│              Pydantic Schema (agents/schemas.py)              │
│   AgentInput → DiagnosisOutput / RecommendationOutput / ...  │
│   LLM 和规则引擎共享同一套 Schema，输出格式完全一致            │
└──────────────────────────────────────────────────────────────┘
```

### LLM 接入计划 / Integration Plan

#### 当前模型 / Current Model

| 配置 | 值 | 说明 |
|------|---|------|
| Provider | 通义千问 (DashScope) | OpenAI 兼容 API |
| Base URL | `https://dashscope.aliyuncs.com/compatible-mode/v1` | DashScope 兼容端点 |
| Model | `qwen-plus` | 通义千问增强版 |
| Output Mode | Structured Outputs | 保证输出严格遵守 Pydantic Schema |
| Fallback | 规则引擎 (当前实现) | LLM 调用失败时自动降级 |

> 💡 **切换模型**：支持任何 OpenAI 兼容 API，只需修改 `.env` 中的 `OPENAI_BASE_URL` 和 `OPENAI_MODEL`。可接入 OpenAI GPT-4o、Azure OpenAI、私有化部署 等。

#### 接入步骤 / Steps to Enable

```bash
# 1. 依赖已包含在 requirements.txt 中（openai >= 1.40.0）

# 2. 配置环境变量（.env 文件）
OPENAI_API_KEY=sk-...                                              # DashScope API Key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1  # 默认通义千问
OPENAI_MODEL=qwen-plus                                             # 默认 qwen-plus
USE_LLM=true                                                       # 启用 LLM

# 3. 无需修改工作流代码 — Agent 函数内部自动切换
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
|-------|──────|
| **Monitor (A1)** | 纯指标阈值扫描，确定性逻辑，无需 LLM |
| **Forecast (A4)** | 现金流预测为数值计算，LLM 不适合数值推理 |
| **Execution (A8)** | 连接器调用，纯代码执行 |

> 💡 **设计原则**：遵循 V3 PRD 原则 1 —「代码主导流程，LLM 只在边界内工作」。数值计算、状态流转、工具调用由代码控制；LLM 仅负责自然语言理解与生成，且输出必须通过 Structured Outputs 钉死在 Schema 上。

---

## 💬 RAG 对话系统 / RAG Conversation

### 架构概览 / Architecture Overview

```
用户提问 → ChromaDB 语义检索 Top-K 相关片段
              ↓
         注入 system prompt 作为增强上下文
              ↓
         LLM 基于增强上下文回答，引用具体 evidence_id
              ↓
         SSE 流式返回 (打字机效果)
```

### 向量化数据源 / Vectorized Data Sources

1. **Agent 分析输出**：diagnosis、recommendations、summary
2. **证据链**：evidence_items 全量向量化
3. **商家基础信息**：商家画像数据

### 核心特性 / Key Features

| 特性 | 说明 |
|------|------|
| **多轮对话** | 支持追问、补充分析、引导分析方向 |
| **对话持久化** | `conversations` + `conversation_messages` 表存储历史 |
| **自动标题生成** | 首轮对话后 LLM 自动生成简短标题 |
| **Markdown 美化** | 大模型回复支持 Markdown 富文本渲染 |
| **上下文注入** | 自动将案件 evidence、metrics、agent_output 注入 LLM 上下文 |
| **向量存储** | ChromaDB 本地嵌入式 + 通义千问 text-embedding-v4 嵌入模型 |

---

## 🔐 认证与用户管理 / Authentication

### 认证流程 / Auth Flow

```
首次启动                              日常使用
─────────                            ─────────
                                     
┌─────────────┐                      ┌─────────────┐
│  GET /check- │                      │  POST /login │
│  init        │                      │  {username,  │
└──────┬──────┘                      │   password}  │
       │                              └──────┬──────┘
       ▼                                     ▼
  initialized?                         验证密码 (bcrypt)
  ├── No ──→ 显示初始化页面                  │
  │          POST /setup ──→ 创建超管        ▼
  │                          自动登录   签发 JWT Token
  │                                    ├─ Access Token (30min)
  └── Yes ──→ 显示登录页面              └─ Refresh Token (7天)
              POST /login                    │
                                             ▼
                                    存入 localStorage
                                    后续请求自动携带
                                    Authorization: Bearer <token>
                                             │
                                             ▼
                                    Token 过期时自动
                                    调用 /refresh 续期
```

### 认证 API / Auth Endpoints

| 方法 | 端点 | 说明 | 认证要求 |
|------|------|------|---------|
| `GET` | `/api/auth/check-init` | 检查系统是否已初始化 | 🔓 公开 |
| `POST` | `/api/auth/setup` | 系统初始化（创建首个超管） | 🔓 公开（仅一次） |
| `POST` | `/api/auth/login` | 用户登录 | 🔓 公开 |
| `POST` | `/api/auth/refresh` | 刷新 Access Token | 🔓 公开 |
| `POST` | `/api/auth/register` | 管理员创建新用户 | 🔒 仅管理员 |
| `POST` | `/api/auth/change-password` | 修改密码 | 🔒 需登录 |
| `GET` | `/api/auth/me` | 获取当前用户信息 | 🔒 需登录 |

### 用户管理 API / User Management Endpoints

| 方法 | 端点 | 说明 | 认证要求 |
|------|------|------|---------|
| `GET` | `/api/users` | 用户列表 | 🔒 仅管理员 |
| `PUT` | `/api/users/{id}/status` | 启用/禁用用户 | 🔒 仅管理员 |
| `PUT` | `/api/users/{id}/role` | 修改用户角色 | 🔒 仅管理员 |
| `POST` | `/api/users/{id}/reset-password` | 重置密码 | 🔒 仅管理员 |
| `DELETE` | `/api/users/{id}` | 删除用户 | 🔒 仅管理员 |

### 安全特性 / Security Features

| 特性 | 实现方式 |
|------|---------|
| 密码存储 | bcrypt 哈希（passlib） |
| Token 签发 | JWT（python-jose + HS256） |
| 双令牌机制 | Access Token (30min) + Refresh Token (7天) |
| 中间件保护 | 所有 API 自动校验 Token（公开路径白名单除外） |
| 超管保护 | 不可删除、不可禁用、不可修改角色 |
| 调试模式 | `DEBUG_AUTH=True` 时支持 `X-User-Role` Header 跳过认证 |

---

## 🔌 API 参考 / API Reference

### 认证 / Authentication

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/auth/check-init` | 检查系统是否已初始化 |
| `POST` | `/api/auth/setup` | 系统初始化（创建首个超级管理员，仅可调用一次） |
| `POST` | `/api/auth/login` | 用户登录，返回 Access + Refresh Token |
| `POST` | `/api/auth/refresh` | 使用 Refresh Token 获取新的 Access Token |
| `POST` | `/api/auth/register` | 管理员创建新用户（需管理员权限） |
| `POST` | `/api/auth/change-password` | 已登录用户修改密码 |
| `GET` | `/api/auth/me` | 获取当前登录用户信息 |

### 用户管理 / User Management

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/users` | 用户列表（仅管理员） |
| `PUT` | `/api/users/{id}/status` | 启用/禁用用户 |
| `PUT` | `/api/users/{id}/role` | 修改用户角色 |
| `POST` | `/api/users/{id}/reset-password` | 管理员重置用户密码 |
| `DELETE` | `/api/users/{id}` | 删除用户（不可删除超管和自己） |

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

### 对话式分析 / Conversational Analysis

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/cases/{id}/conversations` | 创建新对话 |
| `GET` | `/api/cases/{id}/conversations` | 对话列表 |
| `POST` | `/api/cases/{id}/conversations/{conv_id}/messages/stream` | 发送消息 (SSE 流式回复) |
| `GET` | `/api/cases/{id}/conversations/{conv_id}/messages` | 对话历史 |

### 可观测面板 / Observability

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/observability/overview` | Agent 运行总览统计 |
| `GET` | `/api/observability/trends` | 近 7 天趋势数据 |
| `GET` | `/api/observability/agents` | 各 Agent 节点耗时排行 |

### 系统 / System

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查 |

> 💡 完整的 API 文档可在后端启动后访问 `http://localhost:8000/docs` (Swagger UI) 或 `http://localhost:8000/redoc` (ReDoc)。

---

## 📊 数据模型 / Data Model

系统共 **28 张数据库表**（MySQL 8.0），完整 ER 图和字段说明请查看 👉 [docs/data-model.md](docs/data-model.md)

### 表概览 / Table Overview

#### 认证与用户表

| # | 表名 | 说明 |
|---|------|------|
| 1 | `users` | 用户（含角色、密码哈希、超管标记、登录时间） |

#### V1/V2 核心业务表

| # | 表名 | 说明 |
|---|------|------|
| 2 | `merchants` | 商家基础信息 |
| 3 | `orders` | 订单 |
| 4 | `returns` | 退货退款 |
| 5 | `logistics_events` | 物流事件 |
| 6 | `settlements` | 结算回款 |
| 7 | `insurance_policies` | 保险保单 |
| 8 | `financing_products` | 融资产品 |
| 9 | `risk_cases` | 风险案件 |
| 10 | `evidence_items` | 证据项 |
| 11 | `recommendations` | 建议 |
| 12 | `reviews` | 案件审批记录 |
| 13 | `audit_logs` | 审计日志 |
| 14 | `financing_applications` | 融资申请 |
| 15 | `claims` | 理赔申请 |
| 16 | `manual_reviews` | 人工复核任务 |

#### V3 多 Agent 生产化表

| # | 表名 | 说明 |
|---|------|------|
| 17 | `workflow_runs` | 工作流运行实例 |
| 18 | `agent_runs` | Agent 运行记录（含版本追踪） |
| 19 | `checkpoints` | 工作流断点 |
| 20 | `approval_tasks` | 审批任务队列 |
| 21 | `tool_invocations` | 工具调用日志（含幂等键） |
| 22 | `prompt_versions` | Prompt 版本管理（含灰度权重） |
| 23 | `schema_versions` | Schema 版本管理 |
| 24 | `eval_datasets` | 评测数据集 |
| 25 | `eval_runs` | 评测运行 |
| 26 | `eval_results` | 评测结果（含 LLM-Judge 评分） |

#### 对话与向量表

| # | 表名 | 说明 |
|---|──────|──────|
| 27 | `conversations` | 对话会话（关联案件，含自动标题） |
| 28 | `conversation_messages` | 对话消息（用户/助手角色） |

> 💡 向量数据存储使用 ChromaDB 独立目录 `backend/vector_data/`，不占用 MySQL 主库。

---

## ⚙️ 配置说明 / Configuration

### 环境变量 / Environment Variables

在 `backend/` 目录下创建 `.env` 文件 / Create `.env` file in `backend/`:

```env
# 数据库（默认 MySQL）/ Database (default MySQL)
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/m_agents

# CORS 允许的来源 / Allowed CORS origins
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]

# LLM 配置 / LLM Config
OPENAI_API_KEY=sk-...                                               # DashScope API Key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1   # 通义千问 (默认)
OPENAI_MODEL=qwen-plus                                              # 模型名称 (默认 qwen-plus)
USE_LLM=true                                                        # 启用 LLM (false 则使用规则引擎)

# JWT 认证 / JWT Authentication (⚠️ 必须配置强随机密钥)
JWT_SECRET_KEY=your-strong-random-secret-key-here                   # 生成方式: openssl rand -hex 32
JWT_ALGORITHM=HS256                                                 # 签名算法
ACCESS_TOKEN_EXPIRE_MINUTES=30                                      # Access Token 过期时间 (分钟)
REFRESH_TOKEN_EXPIRE_DAYS=7                                         # Refresh Token 过期时间 (天)

# 向量存储 (RAG 对话系统) / Vector Store (RAG Conversation)
VECTOR_STORE_DIR=                                                   # 空字符串使用默认路径 backend/vector_data/
EMBEDDING_MODEL=text-embedding-v4                                   # 阿里云通义嵌入模型
EMBEDDING_BATCH_SIZE=6                                              # 嵌入请求批量大小
RAG_TOP_K=5                                                         # 语义检索返回的最相关文档数

# 日志配置 / Logging Config
LOG_LEVEL=INFO                                                      # 日志级别
LOG_FORMAT=simple                                                   # 日志格式 (simple / json)
LOG_FILE_ENABLED=true                                               # 启用文件日志 (true / false)
LOG_DIR=logs                                                        # 日志目录 (相对 backend/ 或绝对路径)
LOG_ROTATION_SIZE=50 MB                                             # 单文件滚动大小
LOG_RETENTION_SIZE=1 GB                                             # 日志目录总大小上限
LOG_COMPRESSION=gz                                                  # 滚动后压缩格式 (gz / 空=禁用)

# 调试模式 / Debug Mode
DEBUG_AUTH=true                                                     # 允许 X-User-Role Header (仅开发)
```

> ⚠️ **安全提醒**：`JWT_SECRET_KEY` 必须使用强随机密钥。推荐使用 `openssl rand -hex 32` 生成。切勿使用默认值或简单字符串。

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
| 管理员 | `admin` | 全部权限（含配置管理、评测管理、用户管理） |

> 💡 **认证模式**：
> - **生产模式**：通过登录获取 JWT Token，中间件自动校验权限。
> - **调试模式** (`DEBUG_AUTH=True`)：可通过 HTTP Header `X-User-Role` 切换角色，无需登录。

---

## 🧪 评测中心 / Evaluation

### 当前状态 / Current Status

评测中心已从 mock 实现升级为**真实 Agent 工作流评测**，每条测试用例走完整的 9-Agent 工作流。引入 **LLM-as-Judge** 对 Agent 输出进行语义级质量评分（正确性、完整性、幻觉检测）。

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
| **LLM-Judge 评分** | **LLM 评委对输出质量的语义评分** | **> 7/10** |
| **平均延迟** | **单次评测用例平均耗时** | **< 30s** |

### 线上抽样 / Online Sampling

```bash
# 从线上 agent_runs 中随机抽样
curl "http://localhost:8000/api/evals/sampling?agent_name=recommendation_agent&sample_size=10"
```

---

## 📡 可观测面板 / Observability

系统内置 Agent 可观测面板（`/observability`），可视化展示 Agent 运行状态：

| 指标 | 说明 |
|------|------|
| 今日分析量 | 当日触发的分析工作流总数 |
| 平均响应时间 | Agent 节点平均耗时 |
| LLM 调用成功率 | LLM 调用成功/失败比例 |
| 降级触发次数 | fallback 到规则引擎的次数 |
| 趋势图表 | 近 7 天响应时间趋势、各 Agent 节点耗时排行 |

数据来源：聚合 `agent_runs`、`workflow_runs` 表中的运行数据。

### 日志文件存储 / Log File Storage

应用日志默认同时写入文件，支持按大小滚动存储（总上限 1GB），旧文件自动 gzip 压缩：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `LOG_FILE_ENABLED` | `true` | 是否启用文件日志 |
| `LOG_DIR` | `logs/` | 日志目录路径 |
| `LOG_ROTATION_SIZE` | `50 MB` | 单文件滚动大小 |
| `LOG_RETENTION_SIZE` | `1 GB` | 总目录大小上限（超出自动删除最旧文件） |
| `LOG_COMPRESSION` | `gz` | 压缩格式（设为空字符串禁用） |

日志文件路径：`backend/logs/app.log`

### 日志可视化 / Log Visualization (Grafana Loki)

推荐使用 **Grafana Loki + Grafana** 进行日志可视化查看和搜索：

```bash
# 一键启动日志可视化平台
cd infra/
docker-compose -f docker-compose.logging.yml up -d

# 访问 Grafana 面板
# http://localhost:3100 (admin/admin)
# 在 Explore 页面选择 Loki 数据源，使用 LogQL 查询日志
```

**LogQL 常用查询示例**：
```logql
# 查看所有错误日志
{app="m-agents"} |= "ERROR"

# 按 trace_id 追踪请求
{app="m-agents"} | trace_id="abc-123"

# 查看特定模块日志
{app="m-agents"} |= "orchestrator"
```

---

## 📜 版本演进 / Changelog

```
V1 (MVP)        V2 (闭环执行)      V3 (多Agent生产化)    V3.1 (认证+LLM)      V4 (体验+健壮)        V5 (智能增强)
────────►─────────────►───────────────────►─────────────────►──────────────────►──────────────────►
• 风险案件分析    • 融资/理赔/复核    • LangGraph 9-Agent   • JWT 认证体系       • 前端视觉重构       • Triage Hybrid 架构
• 3 Agent 编排    • 执行闭环          • 审批门禁 + 守卫      • 用户管理 CRUD      • 侧边导航+设计系统  • Evidence LLM 分析
• 规则引擎        • 任务状态机        • Checkpoint 持久化    • 通义千问 LLM 接入   • 中文状态映射       • Agent 上下文传递
• 案件列表/详情   • 审批服务          • 三级降级 L1/L2/L3   • bcrypt 密码哈希    • SSE 工作流可视化    • Expert Prompt 升级
                                    • RBAC 5 角色         • Token 自动刷新     • LLM IO 流式展示    • ChromaDB RAG 对话
                                    • 评测中心            • 认证中间件         • 工程健壮性 V1      • Prompt 版本运行时
                                    • Prompt/Schema 版本                       • pytest 测试框架    • 对话式分析+可观测
                                    • 灰度开关                                 • loguru 统一日志    • LLM-Judge 评测
                                    • 工具注册中心                              • Toast 通知系统     • UI 打磨+Markdown
                                    • 46 API 端点                              • 工程健壮性 V2      • 60+ API 端点
                                                                               • SQLite → MySQL
                                                                               • LLM 超时保护
                                                                               • JWT 安全加固
                                                                               • 依赖版本锁定
```

---

## 🗺 路线图 / Roadmap

- [x] 🔌 接入真实 LLM — 通义千问 qwen-plus (A3/A5/A7/A9)
- [x] 🔑 JWT 认证 + 用户管理体系
- [x] 🛡 认证中间件 + RBAC 权限校验
- [x] 🎨 前端视觉重构（侧边导航 + 设计系统 + 共享组件）
- [x] 🏷 前端中文状态名称和 Agent 中文名映射
- [x] 📡 SSE 实时分析工作流进度推送
- [x] 🤖 LLM Agent IO 流式展示（Prompt + 大模型回复打字机效果）
- [x] 🧪 pytest 测试框架 + 全局异常处理 + Toast 通知
- [x] 📝 loguru 统一日志框架
- [x] 🗄 SQLite → MySQL 数据库迁移
- [x] ⏱ LLM 调用超时保护 + JWT 安全加固
- [x] 📦 依赖版本锁定 (主版本上界约束)
- [x] 💬 对话式分析系统（RAG + ChromaDB + SSE 流式）
- [x] 📊 Agent 可观测面板（运行统计 + 趋势分析）
- [x] 🧠 Triage Hybrid 架构（规则 + LLM 精细分类）
- [x] 🔍 Evidence Agent LLM 分析层（动态评分 + 关联分析）
- [x] 🔗 Agent 间累积式上下文传递 (analysis_context)
- [x] ✍️ Expert Prompt 升级（CoT + Few-Shot + 反面约束）
- [x] 📚 ChromaDB 向量数据库 + RAG 对话增强
- [x] 🔄 Prompt 版本运行时加载 + 灰度分流
- [x] 🧪 真实 Agent 工作流评测 + LLM-as-Judge
- [x] 💅 UI 打磨（Markdown 渲染 + 字段中文化 + 对话增强）
- [ ] 📈 Prometheus + Grafana 监控集成
- [ ] 🔒 OAuth 2.0 / SSO 集成
- [ ] 🧪 端到端评测流水线 (CI/CD)
- [ ] 🌐 多租户隔离
- [ ] 📱 移动端审批
- [ ] 🤖 接入 OpenAI Agents SDK Guardrails

---

## 📄 许可证 / License

本项目采用 [MIT License](LICENSE) 开源协议。

This project is licensed under the [MIT License](LICENSE).
