# 基础设施与运维设计

> 商家经营保障 Agent V3 — 后端技术设计文档（版本基线：V5）
>
> 相关文档：[后端架构概览](./backend-architecture-overview.md) | [多 Agent 智能体系统设计](./backend-agent-system-design.md) | [API 接口与数据模型](./backend-api-data-design.md)

---

## 1. JWT 认证鉴权架构

### 1.1 双令牌机制

系统采用 **Access Token + Refresh Token** 双令牌认证方案：

| 令牌类型 | 有效期 | 用途 | 存储位置 |
|----------|--------|------|----------|
| Access Token | 30 分钟（`ACCESS_TOKEN_EXPIRE_MINUTES`） | API 请求鉴权 | 前端内存 / localStorage |
| Refresh Token | 7 天（`REFRESH_TOKEN_EXPIRE_DAYS`） | 刷新 Access Token | 前端 localStorage |

两种 Token 均为 HS256 签名的 JWT，通过 `type` 字段区分（`"access"` / `"refresh"`）。

### 1.2 认证流程时序图

```mermaid
sequenceDiagram
    participant 用户 as 用户浏览器
    participant API as FastAPI 后端
    participant MW as AuthMiddleware
    participant Sec as security.py
    participant DB as MySQL

    Note over 用户,DB: 登录流程
    用户->>API: POST /api/auth/login {username, password}
    API->>DB: 查询 User 表
    API->>Sec: verify_password(plain, hash)
    Sec-->>API: ✅ 密码匹配
    API->>Sec: create_access_token({sub: user_id, role, username})
    API->>Sec: create_refresh_token({sub: user_id})
    API-->>用户: {access_token, refresh_token, user}

    Note over 用户,DB: 请求鉴权流程
    用户->>API: GET /api/risk-cases<br/>Authorization: Bearer {access_token}
    API->>MW: dispatch(request)
    MW->>Sec: decode_token(token)
    Sec-->>MW: payload {sub, role, type: "access"}
    MW->>MW: 注入 request.state.user_role
    MW->>MW: 查找 PATH_PERMISSIONS 权限要求
    MW->>MW: has_permission(role, required_perm)
    MW-->>API: ✅ 放行
    API-->>用户: 200 {items: [...]}

    Note over 用户,DB: Token 刷新流程
    用户->>API: POST /api/auth/refresh {refresh_token}
    API->>Sec: decode_token(refresh_token)
    Sec-->>API: payload {sub, type: "refresh"}
    API->>Sec: create_access_token(...)
    API-->>用户: {access_token, refresh_token}
```

### 1.3 RBAC 角色权限矩阵

系统定义 **5 种角色** 和 **18 种权限**（`core/rbac.py`）：

| 权限 | risk_ops | finance_ops | claim_ops | compliance | admin |
|------|:--------:|:-----------:|:---------:|:----------:|:-----:|
| VIEW_CASES | ✅ | ✅ | ✅ | ✅ | ✅ |
| TRIGGER_ANALYSIS | ✅ | ❌ | ❌ | ❌ | ✅ |
| REOPEN_CASE | ✅ | ❌ | ❌ | ❌ | ✅ |
| VIEW_APPROVALS | ✅ | ✅ | ✅ | ✅ | ✅ |
| APPROVE_FRAUD_REVIEW | ✅ | ❌ | ❌ | ✅ | ✅ |
| APPROVE_FINANCE | ❌ | ✅ | ❌ | ✅ | ✅ |
| APPROVE_CLAIM | ❌ | ❌ | ✅ | ✅ | ✅ |
| VIEW_WORKFLOWS | ✅ | ✅ | ✅ | ✅ | ✅ |
| RETRY_WORKFLOW | ❌ | ❌ | ❌ | ❌ | ✅ |
| RESUME_WORKFLOW | ❌ | ❌ | ❌ | ❌ | ✅ |
| MANAGE_PROMPTS | ❌ | ❌ | ❌ | ❌ | ✅ |
| MANAGE_SCHEMAS | ❌ | ❌ | ❌ | ❌ | ✅ |
| MANAGE_MODELS | ❌ | ❌ | ❌ | ❌ | ✅ |
| VIEW_EVALS | ✅ | ✅ | ✅ | ✅ | ✅ |
| CREATE_EVALS | ❌ | ❌ | ❌ | ❌ | ✅ |
| VIEW_AUDIT | ✅ | ❌ | ❌ | ✅ | ✅ |
| MODIFY_RECOMMENDATIONS | ❌ | ✅ | ✅ | ❌ | ✅ |

### 1.4 认证中间件流程（`core/auth_middleware.py`）

```mermaid
graph TB
    A["请求进入"] --> B{"路径在<br/>PUBLIC_PATHS?"}
    B -->|是| C["跳过认证，直接放行"]
    B -->|否| D{"Authorization<br/>Header?"}
    D -->|有 Bearer Token| E["decode_token()"]
    E -->|无效/过期| F["401 Token 无效"]
    E -->|有效| G{"type = access?"}
    G -->|否| H["401 请使用 Access Token"]
    G -->|是| I["注入 user_id/role"]
    D -->|无| J{"DEBUG_AUTH<br/>= True?"}
    J -->|是| K["读取 X-User-Role Header"]
    K -->|有效角色| I
    K -->|无效角色| L["401 无效角色"]
    J -->|否| M["401 未提供认证信息"]
    I --> N{"匹配<br/>PATH_PERMISSIONS?"}
    N -->|无需权限| O["放行"]
    N -->|需要权限| P{"has_permission<br/>(role, perm)?"}
    P -->|是| O
    P -->|否| Q["403 权限不足"]
```

**公开路径**（无需认证）：`/health`, `/docs`, `/openapi.json`, `/redoc`, `/api/auth/login`, `/api/auth/refresh`, `/api/auth/setup`, `/api/auth/check-init`

### 1.5 密码安全策略

- 使用 **bcrypt** 算法哈希密码（`passlib.context.CryptContext`）
- JWT 密钥通过 `.env` 文件配置 `JWT_SECRET_KEY`
- 非调试模式下，JWT 密钥必须至少 32 个字符（`Settings._validate_security` 校验）
- DEBUG_AUTH 模式允许通过 `X-User-Role` Header 传入角色，仅用于开发阶段

---

## 2. RAG 对话系统设计

### 2.1 向量存储架构

```mermaid
graph TB
    subgraph "ChromaDB 向量存储 (core/vector_store.py)"
        Client["PersistentClient<br/>持久化到 vector_data/"]
        Col["Collection: case_{id}<br/>索引方式: HNSW (cosine)"]
        EF["嵌入函数:<br/>OpenAICompatibleEmbedding<br/>模型: text-embedding-v4"]
    end

    subgraph "数据源"
        D1["Agent 分析输出<br/>(case_summary, root_causes, recommendations)"]
        D2["证据链<br/>(evidence_items)"]
        D3["商家基础信息<br/>(merchants)"]
    end

    D1 & D2 & D3 --> |"index_case_data()"| Col
    Col --> |"search_case_context()"| R["语义检索结果"]
    EF --> Col
```

**关键配置**：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `VECTOR_STORE_DIR` | `backend/vector_data/` | ChromaDB 持久化目录 |
| `EMBEDDING_MODEL` | `text-embedding-v4` | 阿里云通义嵌入模型 |
| `EMBEDDING_BATCH_SIZE` | 6 | 嵌入请求批量大小（text-embedding-v4 限制较严） |
| `RAG_TOP_K` | 5 | 语义检索返回的最相关文档数 |

### 2.2 文档向量化流程

`index_case_data(case_id)` 将案件数据拆分为以下文档类型并向量化：

| 文档类型 | 来源 | metadata.source | 示例文本 |
|----------|------|-----------------|----------|
| 案件摘要 | agent_output.case_summary | summary_agent | "商家近期退货率异常上升..." |
| 根因分析 | agent_output.root_causes[] | diagnosis_agent | "根因: 退货率激增 — 近7日退货率..." |
| 动作建议 | agent_output.recommendations[] | recommendation_agent | "建议[business_loan]: 申请经营贷..." |
| 现金流预测 | agent_output.cash_gap_forecast | forecast_agent | "现金流预测: 预计14日内缺口¥50,000" |
| 证据项 | evidence_items 表 | evidence_agent | "[order] 订单金额异常波动" |
| 商家信息 | merchants 表 | merchant_profile | "商家: XX旗舰店, 行业: 数码" |

### 2.3 语义检索策略

`search_case_context(case_id, query, top_k=5)`：

1. 获取案件对应的 Collection（`case_{case_id}`）
2. 检查 Collection 是否有数据（空集合跳过检索）
3. 调用 `collection.query()` 进行余弦相似度检索
4. 返回 Top-K 结果，每条包含 `document`、`metadata`、`distance`

### 2.4 RAG 对话流程

```mermaid
sequenceDiagram
    participant 用户 as 前端
    participant API as conversations.py
    participant Vec as vector_store
    participant LLM as 通义千问

    用户->>API: POST /conversations/{id}/chat/stream<br/>{message: "为什么退货率异常?"}

    API->>Vec: search_case_context(case_id, query)
    Vec-->>API: 检索结果 passages[]

    alt ChromaDB 可用 且 有检索结果
        API->>API: 构建 RAG Prompt<br/>(System: 你是分析助手 + 检索上下文 + 对话历史)
    else ChromaDB 不可用 或 无检索结果
        API->>API: 降级: 使用 case.agent_output_json 作为上下文
    end

    API->>LLM: chat_completion_stream(messages)
    loop 每个 chunk
        LLM-->>API: delta text
        API-->>用户: event: message_chunk {content}
    end
    API->>DB: 保存 assistant 消息
    API-->>用户: event: done
```

### 2.5 降级策略

| 场景 | 降级行为 | 用户感知 |
|------|----------|----------|
| ChromaDB 模块未安装 | 启动日志警告，对话使用 `agent_output_json` 作为上下文 | 对话质量略有下降，但功能正常 |
| ChromaDB 初始化失败 | 同上 | 同上 |
| Collection 为空（未索引） | 跳过语义检索，回退到 `agent_output_json` | 同上 |
| 嵌入 API 调用失败 | 自动降低 batch_size 重试，最终失败回退到 ChromaDB 默认嵌入 | 首次检索延迟增加 |

---

## 3. 评测中心设计

### 3.1 数据集管理

- **创建**：`POST /api/evals/datasets` — 手动创建空数据集
- **从历史案件导入**：`POST /api/evals/datasets/import-from-cases` — 选择已分析的案件自动导入
- **存储格式**：`test_cases_json` 字段存储 JSON 数组，每个测试用例包含：
  - `case_id` — 案件 ID
  - `merchant_id` — 商家 ID
  - `expected_risk_level` — 期望的风险等级
  - `expected_root_causes` — 期望的根因标签
  - `agent_output_json` — 基准输出（作为参考答案）

### 3.2 评测运行引擎

```mermaid
graph TB
    A["POST /api/evals/runs<br/>{dataset_id, model_name}"] --> B["创建 EvalRun 记录"]
    B --> C["启动后台线程"]
    C --> D["遍历 test_cases"]
    D --> E["对每个 test_case 执行完整工作流"]
    E --> F["收集 actual_output"]
    F --> G{"启用 LLM-Judge?"}
    G -->|是| H["调用 LLM 评分<br/>judge_score, judge_reasoning"]
    G -->|否| I["规则评分<br/>schema_valid, adopted 等"]
    H --> J["保存 EvalResult"]
    I --> J
    J --> K{"还有测试用例?"}
    K -->|是| D
    K -->|否| L["聚合统计<br/>更新 EvalRun"]
```

**执行方式**：使用 `threading.Thread` 异步执行（避免阻塞 API 请求），通过 `completed_count` / `total_count` 追踪进度。

### 3.3 LLM-as-Judge 评分机制

评分维度和权重：

| 维度 | 说明 | 评分方式 |
|------|------|----------|
| `judge_score` | 综合评分（0-100） | LLM 根据 expected vs actual 输出综合评判 |
| `judge_reasoning` | 评分理由 | LLM 生成自然语言解释 |
| `schema_valid` | Schema 合格性（0/1） | Pydantic 校验 |
| `risk_level_match` | 风险等级匹配（0/1） | 精确匹配 |
| `root_cause_match` | 根因覆盖（0/1） | 标签集合交集检查 |
| `has_hallucination` | 是否存在幻觉（0/1） | LLM 判断 |
| `evidence_covered` | 证据覆盖率（0/1） | 证据 ID 包含检查 |

**聚合指标**（`EvalRun` 级别）：
- `adoption_rate` — 采纳率
- `rejection_rate` — 驳回率
- `evidence_coverage_rate` — 证据覆盖率
- `schema_pass_rate` — Schema 合格率
- `hallucination_rate` — 幻觉率
- `avg_judge_score` — 平均 Judge 评分
- `avg_latency_ms` — 平均延迟

---

## 4. 配置管理

### 4.1 pydantic-settings 配置层次

`core/config.py` 使用 `pydantic-settings` 实现类型安全的分层配置：

```mermaid
graph TB
    A["代码中的默认值<br/>(Settings 类字段默认)"] --> D["最终 settings 实例"]
    B[".env 文件<br/>(env_file='.env')"] --> D
    C["环境变量<br/>(最高优先级)"] --> D
    style C fill:#f9f,stroke:#333,stroke-width:2px
```

**优先级**：环境变量 > `.env` 文件 > 代码默认值

### 4.2 配置分组

| 分组 | 配置项 | 默认值 | 说明 |
|------|--------|--------|------|
| **数据库** | `DATABASE_URL` | `mysql+pymysql://...` | 数据库连接字符串 |
| **CORS** | `CORS_ORIGINS` | `["localhost:3000"]` | 允许的跨域源 |
| **风险阈值** | `RETURN_RATE_AMPLIFICATION_THRESHOLD` | 1.6 | 退货率放大阈值 |
| | `PREDICTED_GAP_THRESHOLD` | 50000.0 | 预测缺口阈值 |
| | `SETTLEMENT_DELAY_THRESHOLD` | 3.0 | 结算延迟阈值（天） |
| | `ANOMALY_SCORE_THRESHOLD` | 0.8 | 异常分数阈值 |
| **LLM** | `OPENAI_API_KEY` | （空） | 通义千问 API Key |
| | `OPENAI_BASE_URL` | `dashscope.aliyuncs.com/...` | DashScope 兼容接口 |
| | `OPENAI_MODEL` | `qwen-plus` | 默认模型 |
| | `USE_LLM` | `true` | 是否启用 LLM |
| **JWT** | `JWT_SECRET_KEY` | （空） | JWT 签名密钥（≥32字符） |
| | `JWT_ALGORITHM` | `HS256` | 签名算法 |
| | `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Access Token 有效期 |
| | `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh Token 有效期 |
| | `DEBUG_AUTH` | `true` | 调试模式开关 |
| **日志** | `LOG_LEVEL` | `INFO` | 日志级别 |
| | `LOG_FILE_ENABLED` | `true` | 是否启用文件日志 |
| | `LOG_DIR` | `logs` | 日志目录 |
| | `LOG_ROTATION_SIZE` | `50 MB` | 单文件滚动大小 |
| | `LOG_RETENTION_SIZE` | `1 GB` | 日志目录总大小上限 |
| | `LOG_COMPRESSION` | `gz` | 压缩格式 |
| **向量存储** | `VECTOR_STORE_DIR` | （空，默认 vector_data/） | ChromaDB 持久化目录 |
| | `EMBEDDING_MODEL` | `text-embedding-v4` | 嵌入模型 |
| | `EMBEDDING_BATCH_SIZE` | 6 | 嵌入批量大小 |
| | `RAG_TOP_K` | 5 | 检索返回数 |

### 4.3 `.env` 文件规范

```bash
# ── 数据库 ──
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/m_agents

# ── LLM ──
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus
USE_LLM=true

# ── JWT 认证 ──
JWT_SECRET_KEY=your-random-secret-key-at-least-32-chars
DEBUG_AUTH=false

# ── 日志 ──
LOG_LEVEL=INFO
LOG_FILE_ENABLED=true
```

---

## 5. 日志框架

### 5.1 Loguru 配置（`core/logging_config.py`）

系统使用 Loguru 替代 Python 标准 logging，提供更简洁的 API 和更丰富的功能。

**双 Sink 架构**：

| Sink | 输出 | 格式 | 颜色 |
|------|------|------|------|
| **控制台**（stderr） | 实时开发调试 | 可选 simple/json/detailed | ✅ ANSI 颜色 |
| **文件**（logs/app.log） | 持久化存储 | detailed（固定） | ❌ 纯文本 |

### 5.2 日志格式

**simple 格式**（默认）：
```
2026-03-21 13:00:00.123 | INFO     | app.main | 🚀 应用启动 | USE_LLM=True
```

**detailed 格式**：
```
2026-03-21 13:00:00.123 | INFO     | app.agents.orchestrator:analyze:200 | trace_id=- | 分析完成
```

**json 格式**：
```json
{"time": "2026-03-21 13:00:00.123", "level": "INFO", "name": "app.main", "function": "setup", "line": 42, "trace_id": "-", "message": "应用启动"}
```

### 5.3 文件轮转策略

```mermaid
graph TB
    A["app.log 写入中"] --> B{"文件大小 ≥<br/>LOG_ROTATION_SIZE?"}
    B -->|是| C["滚动：重命名为<br/>app.2026-03-21_12-00-00.log"]
    C --> D{"LOG_COMPRESSION<br/>配置?"}
    D -->|gz| E["压缩为 .log.gz"]
    D -->|空| F["保留原始 .log"]
    E --> G["检查目录总大小"]
    F --> G
    G --> H{"总大小 ≥<br/>LOG_RETENTION_SIZE?"}
    H -->|是| I["按修改时间升序<br/>删除最旧的文件<br/>（跳过 app.log）"]
    H -->|否| J["完成"]
    I --> J
    B -->|否| J
```

**自定义 retention 函数**：`_make_retention_by_total_size()` — 基于日志目录总大小清理（而非按文件数量或时间），确保磁盘使用量可控。

### 5.4 日志采集链路（Docker 环境）

```mermaid
graph LR
    A["Backend<br/>Loguru"] -->|写入| B["app.log<br/>/app/logs/ 卷"]
    B -->|读取| C["Promtail<br/>日志采集"]
    C -->|推送| D["Loki<br/>日志存储"]
    D -->|查询| E["Grafana<br/>可视化面板"]
```

---

## 6. LLM 客户端（`core/llm_client.py`）

### 6.1 客户端封装

| 函数 | 用途 | 返回 |
|------|------|------|
| `chat_completion()` | 标准聊天补全 | 完整文本 |
| `chat_completion_stream()` | 流式聊天补全 | 逐 chunk 回调 + 完整文本 |
| `structured_output()` | 结构化输出（Pydantic 模型） | 解析后的模型实例 |
| `is_llm_enabled()` | 检查 LLM 是否可用 | 布尔值 |
| `load_prompt()` | 加载 Agent Prompt（DB 优先） | (content, version) |

### 6.2 超时与重试

- **连接超时**：10 秒（`httpx.Timeout(connect=10.0)`）
- **读取超时**：60 秒（`httpx.Timeout(60.0)`）
- **无内置重试**：重试由 `workflow/retry.py` 的三级降级策略统一管理
- **懒加载单例**：OpenAI 客户端在首次调用时初始化，全局复用

### 6.3 Structured Output 降级

```mermaid
graph LR
    A["structured_output(response_model)"] --> B{"beta.parse()<br/>Structured Outputs"}
    B -->|成功| C["返回 Pydantic 实例"]
    B -->|失败| D["降级: JSON 模式"]
    D --> E["追加 Schema 提示"]
    E --> F["response_format=json_object"]
    F --> G["model_validate_json()"]
    G --> C
```

### 6.4 LLM 事件数据类

`LlmEvent` 用于 Agent → SSE 推送链路：

| event_type | 触发时机 | 携带数据 |
|-----------|----------|----------|
| `llm_input` | Agent 发送 Prompt 前 | system_prompt, user_prompt |
| `llm_chunk` | 流式输出每个 delta | content (delta text) |
| `llm_done` | LLM 响应完成 | content (完整回复), elapsed_ms |

---

## 7. Prompt 管理（`core/prompt_loader.py`）

### 7.1 加载机制

```mermaid
graph TB
    A["Agent 请求 Prompt"] --> B{"内存缓存<br/>TTL 60s?"}
    B -->|命中| C["返回缓存"]
    B -->|未命中/过期| D["查询 prompt_versions 表"]
    D --> E{"有 ACTIVE 版本?"}
    E -->|是| F{"有灰度 DRAFT<br/>canary_weight > 0?"}
    F -->|是| G{"random() < canary_weight?"}
    G -->|命中灰度| H["返回 DRAFT 版本"]
    G -->|未命中| I["返回 ACTIVE 版本"]
    F -->|否| I
    E -->|否| J["Fallback: 代码硬编码默认 Prompt"]
    H --> K["写入缓存"]
    I --> K
    J --> K
```

### 7.2 灰度分流

- `canary_weight` 字段（0.0 ~ 1.0）控制灰度流量比例
- 示例：`canary_weight=0.1` 表示 10% 流量使用灰度版本
- 通过 `POST /api/prompt-versions` 创建带 canary_weight 的 DRAFT 版本
- 灰度验证通过后，使用 `POST /api/prompt-versions/{id}/activate` 激活为 ACTIVE

---

## 8. Docker 部署架构

### 8.1 服务编排图

```mermaid
graph TB
    subgraph "Docker Compose"
        subgraph "业务服务"
            MySQL["mysql:8.0<br/>:3306"]
            Backend["FastAPI Backend<br/>(Python)"]
            Frontend["Next.js Frontend<br/>(Node.js)"]
            Nginx["Nginx<br/>:80 → 外部"]
        end

        subgraph "可观测性"
            Loki["Loki 2.9.4<br/>:3200→3100"]
            Promtail["Promtail 2.9.4"]
            Grafana["Grafana 10.3.1<br/>:3100→3000"]
        end
    end

    Nginx -->|"/ → frontend:3000"| Frontend
    Nginx -->|"/api → backend:8000"| Backend
    Backend --> MySQL
    Backend -->|写日志| LogVol["app-logs 卷"]
    Promtail -->|读日志| LogVol
    Promtail --> Loki
    Grafana --> Loki
```

### 8.2 端口映射

| 服务 | 容器端口 | 主机端口 | 可配置变量 |
|------|----------|----------|-----------|
| MySQL | 3306 | `${MYSQL_PORT:-3306}` | `MYSQL_PORT` |
| Nginx | 80 | `${NGINX_PORT:-80}` | `NGINX_PORT` |
| Loki | 3100 | 3200 | — |
| Grafana | 3000 | `${GRAFANA_PORT:-3100}` | `GRAFANA_PORT` |
| Backend | 8000 | 不直接暴露（通过 Nginx 代理） | — |
| Frontend | 3000 | 不直接暴露（通过 Nginx 代理） | — |

### 8.3 健康检查

| 服务 | 检查方式 | 间隔 | 超时 | 重试 | 启动等待 |
|------|----------|------|------|------|----------|
| MySQL | `mysqladmin ping` | 10s | 5s | 5 | 30s |
| Backend | `curl -f http://localhost:8000/health` | 30s | 10s | 3 | 15s |

### 8.4 数据卷

| 卷名 | 用途 | 挂载容器 |
|------|------|----------|
| `mysql-data` | MySQL 数据持久化 | mysql |
| `app-logs` | 后端日志（Loguru 写入，Promtail 读取） | backend (rw), promtail (ro) |
| `loki-data` | Loki 索引和块存储 | loki |
| `grafana-data` | Grafana 仪表板和配置 | grafana |

### 8.5 服务依赖顺序

```
mysql (healthy) → backend (healthy) → frontend → nginx
                                    → loki → promtail, grafana
```

---

## 9. 演进建议

| 方向 | 建议 | 优先级 |
|------|------|--------|
| **密钥管理** | 生产环境引入 HashiCorp Vault 或云密钥管理服务，取代 .env 文件存储敏感信息 | 高 |
| **日志结构化** | 默认使用 JSON 格式日志，便于 Loki 解析和查询 | 中 |
| **指标采集** | 引入 Prometheus + Grafana 指标面板，监控 API QPS、延迟、错误率 | 中 |
| **向量数据库** | 大规模场景下迁移到 Milvus 或 Weaviate，支持分布式部署 | 低 |
| **CI/CD** | 添加 GitHub Actions / GitLab CI 流水线，自动化测试和 Docker 镜像构建 | 高 |
