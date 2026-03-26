# 简历项目描述 —— 商家经营保障 Agent

> 面向 Agent 开发工程师岗位面试，提供 3 种格式的项目描述，按需选用。

---

## 一、STAR 原则版本（推荐用于简历项目经历栏）

### Situation（背景）

电商平台每天面临大量商家风险事件——退货率异常飙升、现金流断裂、疑似欺诈行为等。传统风控依赖人工排查，单个案件分析耗时数小时，且容易遗漏关键风险信号，效率和覆盖率均难以满足业务增长需求。

### Task（任务）

独立设计并开发一套基于多 Agent 协作的智能风控分析系统，实现从风险识别到处置执行的全链路自动化，替代人工分析流程。核心技术挑战包括：多 Agent 状态编排与协作、LLM 输出结构化与降级容灾、RAG 语义对话实现、以及生产级工程化落地（权限、审批、评测、灰度）。

### Action（行动）

- **多 Agent 协作架构（Multi-Agent Pipeline + Conditional Routing）**：对比 ReAct、Plan-and-Execute、Hierarchical 等 Agent 模式后，选择 Multi-Agent Pipeline + 条件路由模式——风控分析是流程明确的领域任务，需要确定性和可审计性，而非 ReAct 的开放探索式推理。基于 LangGraph 设计 7 个专业 Agent（分诊、证据收集、根因分析、处置建议、合规审查、报告生成、执行落地）+ 1 个 Orchestrator 编排器，构建 14 节点有状态工作流，实现条件路由、断点恢复和累积式上下文传递。其中 Triage Agent 采用 Hybrid 三级决策（规则快筛→LLM 研判→安全网兜底），Diagnosis Agent 内部运用 CoT 推理链深度分析根因，Compliance Guard 实现跨 Agent 校验（Reflection 模式变体）。
- **LLM 工程化**：采用通义千问（qwen-plus）作为推理引擎，实现 Structured Output + JSON 模式双降级保障结构化输出可靠性；设计 Prompt 灰度分流机制支持新版 Prompt 按流量比例灰度上线；搭建 LLM-as-Judge 评测中心自动评估分析质量（综合评分、幻觉检测、证据覆盖率）。
- **三级降级容灾**：L1 自动重试（指数退避，覆盖全部 14 节点）→ L2 规则引擎降级（LLM 不可用时用预置规则兜底）→ L3 人工接管（创建工单，工作流暂停等待处理），确保 LLM 完全不可用时系统仍可完成基本风险评估。
- **RAG 语义对话**：分析完成后自动将案件数据按 6 种文档类型切片并向量化存入 ChromaDB（text-embedding-v4, 1024 维），支持用户用自然语言追问分析结果，通过 HNSW 余弦相似度 Top-5 召回 + SSE 流式推送实现实时对话体验。
- **生产级工程化**：6 层分层架构，RBAC 权限体系（5 种角色 × 18 种权限），JWT 双令牌认证，完整审批闭环（AI 建议需审批后方可执行），Docker Compose 一键部署（MySQL + Backend + Frontend + Nginx + Loki + Grafana）。

### Result（成果）

- 分析效率从人工数小时提升到系统自动几分钟完成，覆盖风险识别→处置执行全链路
- 系统规模：7 Agent + 14 节点工作流 + 27 张数据库表 + 11 个路由模块
- 已完成 V1 到 V5 共 5 个版本迭代，具备生产级部署能力
- 三级降级机制保障系统在 LLM 服务异常时仍可提供基本风控能力

---

## 二、精简版本（适合简历项目列表，空间有限时使用）

**商家经营保障 Agent** — 多 Agent 智能风控分析系统
**技术栈**：FastAPI + LangGraph + 通义千问 + ChromaDB + MySQL + Docker
**项目描述**：独立设计开发基于 7 Agent 协作的全链路智能风控系统。对比 ReAct/Plan-and-Execute 等模式后，选择 Multi-Agent Pipeline + 条件路由架构，使用 LangGraph 构建 14 节点有状态工作流，实现条件路由和断点恢复；Triage Agent 采用规则+LLM Hybrid 三级决策，Diagnosis Agent 运用 CoT 推理链；设计三级降级容灾机制（自动重试→规则兜底→人工接管）保障生产可用性；基于 ChromaDB 实现 RAG 语义对话支持分析结果追问；搭建 RBAC 权限体系（5 角色 × 18 权限）、Prompt 灰度分流和 LLM-as-Judge 评测中心。系统将分析效率从人工数小时缩短至分钟级，已迭代 5 个版本，具备生产级部署能力。

---

## 三、技术亮点版本（适合技术面试深度追问准备）

### 1. Agent 设计模式选型与协作架构

- **架构模式选型**：对比 ReAct（Thought-Action-Observation 循环）、Plan-and-Execute（动态规划+执行）、Hierarchical（层级式）等主流 Agent 模式后，选择 **Multi-Agent Pipeline + Conditional Routing** 模式。选型理由：风控分析是流程明确的领域任务，需要每步可追踪、可审计、可回放，而非 ReAct 的开放探索式推理；同时生产环境要求可预测的执行路径，便于实现三级降级和断点恢复，Plan-and-Execute 的动态 re-plan 反而增加不确定性
- **Hybrid 决策模式（Triage Agent）**：融合规则引擎与 LLM 的三级决策——L1 规则快筛覆盖确定区间，L2 LLM 研判处理模糊区间，L3 安全网兜底极端情况，兼顾决策效率与推理能力
- **CoT 推理链（Diagnosis Agent）**：虽然整体架构不采用 ReAct，但在单 Agent 内部运用 Chain-of-Thought 推理链引导 LLM 进行多步根因分析，提升诊断深度
- **Cross-Agent Validation（Reflection 变体）**：Compliance Guard 对上游 Recommend Agent 的输出做质量校验，LLM-as-Judge 评测中心评估分析质量，实现跨 Agent 的反思与纠错机制
- **LangGraph 有状态编排**：基于 StateGraph 构建 14 节点工作流，`GraphState` 在节点间传递，每个 Agent 的输出自动成为下游输入上下文
- **条件路由**：3 个条件路由节点，分诊结果决定处理路径，合规校验结果决定放行或阻断
- **断点恢复**：工作流在审批等待节点自动暂停，审批通过后从断点恢复执行，无需重跑全流程
- **累积式上下文**：`analysis_context` 机制实现 Agent 间洞察接力传递（单条上限 200 字符，总上下文上限 1500 字符，超限 FIFO 淘汰），平衡信息传递与 Token 成本

### 2. LLM 工程化

- **Structured Output 双降级**：优先使用 `beta.parse()` 结构化输出，失败后自动降级到 `response_format=json_object` 模式，再通过 Pydantic v2 Schema 校验，保障 Agent 始终输出合法结构化数据
- **Prompt 灰度分流**：支持新版 Prompt 按流量比例灰度上线（如先给 10% 流量试水），验证通过再全量发布，避免 Prompt 变更引发全局风险
- **LLM-as-Judge 评测中心**：用 LLM 当裁判自动评估分析质量，评测维度包括综合评分、幻觉检测、证据覆盖率，为 Prompt 迭代提供量化依据

### 3. RAG 语义对话

- **6 种文档切片策略**：按语义单元（案件摘要、根因分析、动作建议、现金流预测、证据项、商家信息）切片而非固定长度，每案件 10~20 片，保证召回完整上下文
- **ChromaDB HNSW 索引**：使用 text-embedding-v4（1024 维）向量化，HNSW 余弦相似度 Top-5 召回，嵌入模型与推理模型同属通义系列，语义空间对齐度高
- **SSE 流式推送**：LLM 生成结果通过 Server-Sent Events 实时流式推送到前端，用户无需等待完整回答生成
- **RAG 降级链**：ChromaDB 不可用 → 降级到默认嵌入模型 → 再降级到全量注入 Prompt，对话功能在任何异常下都可用

### 4. 生产级工程化

- **三级降级容灾**：L1 指数退避自动重试（1s→2s→4s，最多 3 次）覆盖全部 14 节点 → L2 规则引擎降级（不依赖 LLM 的风控评估）→ L3 人工接管工单，确保 LLM 完全不可用时系统仍可运行
- **RBAC 权限体系**：5 种角色 × 18 种权限矩阵，JWT 双令牌机制（Access + Refresh），细粒度控制 API 访问权限
- **审批闭环**：AI 的处置建议不会直接执行，必须经过对应角色审批后才能落地，确保人在回路
- **Docker Compose 一键部署**：MySQL + Backend + Frontend + Nginx + Loki + Grafana 全栈容器化，一条命令启动完整环境

---

## 四、面试高频追问预测（附参考回答思路）

### Q1：你为什么选择 Multi-Agent Pipeline 而不是 ReAct？

> **答题思路**：从场景需求出发——风控分析是流程明确的领域任务（分诊→取证→诊断→建议→审批→执行），每一步都需要可追踪、可审计、可回放。ReAct 的 Thought-Action-Observation 循环适合开放性任务（如搜索+问答），但在风控场景中，我们更需要确定性和可预测性。此外，预定义的工作流使得三级降级容灾和断点恢复的实现更加自然，而 ReAct 的动态决策路径会使降级策略变得极其复杂。

### Q2：Plan-and-Execute 不是更灵活吗？为什么不用？

> **答题思路**：Plan-and-Execute 的核心优势是动态 re-plan——执行过程中根据中间结果调整计划。但在生产级风控系统中，可预测的执行路径比灵活性更重要。原因有三：①降级容灾需要明确知道每个节点的失败处理策略；②审批闭环要求执行路径对审批人透明可见；③日志审计需要完整的执行轨迹。不过我的 Triage Agent 输出的 `recommended_path` 某种程度上有"轻量级规划"的意味——分诊结果决定后续走哪条路径，这是在确定性框架内引入的有限灵活性。

### Q3：你的项目里有没有用到 ReAct 的思想？

> **答题思路**：虽然整体架构不是 ReAct，但在单个 Agent 内部借鉴了其理念。例如 Diagnosis Agent 使用 CoT（Chain-of-Thought）推理链，引导 LLM 先分析数据特征→再关联风险因子→最后得出根因结论，这与 ReAct 的 Thought 环节异曲同工。区别在于：ReAct 的 Action 是 Agent 自主选择调用什么工具，而我的 Agent 的"Action"（如查询哪些指标、分析什么数据）是由工作流预定义的。

### Q4：如果让你加入 ReAct 能力，你会怎么改造？

> **答题思路**：最适合引入 ReAct 的是 Evidence Agent（证据收集）。目前它按预定义逻辑查询固定数据源，如果改造为 ReAct 模式，可以让它自主决定"接下来该从哪个数据源收集什么证据"——比如先查退货率→发现异常→自主决定再查商品评价数据→发现差评集中在某SKU→继续深挖该SKU的供应链数据。这样能提升证据收集的深度和覆盖面。改造方式：将各数据源查询封装为 LangChain Tools，让 Evidence Agent 在循环中调用。

### Q5：Hybrid 三级决策和 ReAct 有什么本质区别？

> **答题思路**：Triage Agent 的 Hybrid 三级决策（规则快筛→LLM 研判→安全网兜底）是一种**确定性分层决策**——哪些走规则、哪些走 LLM、哪些走兜底，边界是预定义的。而 ReAct 是**自主决策循环**——Agent 自己决定下一步做什么。两者解决不同的问题：Hybrid 解决的是"如何在效率和智能之间取平衡"，ReAct 解决的是"如何让 Agent 自主探索未知任务"。

### Q6：你的 Cross-Agent Validation 和 Reflection 模式有什么异同？

> **答题思路**：标准 Reflection 是同一个 Agent 生成输出后自我评估、自我改进（Generator→Critic→Re-generate 循环）。我的 Compliance Guard 是**另一个 Agent** 对上游 Recommend Agent 的输出做校验，所以更准确地说是 Cross-Agent Validation。区别在于：Reflection 是自我反思，Cross-Agent Validation 引入了"第二视角"，类似人类团队中的 Code Review——写代码的人和审代码的人不是同一个人，能发现更多盲点。此外，LLM-as-Judge 评测中心也可以看作一种离线的 Reflection 机制，用于 Prompt 迭代。

### Q7：你了解 LangChain 生态吗？为什么工具调用没有用 LangChain Tools？

> **答题思路**：项目使用了 LangGraph（属于 LangChain 生态），但工具调用采用了自建的工具注册中心而非 LangChain Tools。原因是：①风控场景的工具（SQL 查询、指标计算、规则引擎）与 LangChain Tools 的"LLM 自主选择调用"范式不匹配——我的工具调用是工作流预定义的，不需要 LLM 来决定调什么工具；②自建注册中心可以精确控制工具的权限、超时、降级策略，这在生产环境中比通用框架更可控。如果未来要引入 ReAct 能力，会考虑将部分工具迁移为 LangChain Tools 或 MCP Tools 格式。

### Q8：如果要引入 MCP 协议，你会怎么设计？

> **答题思路**：MCP（Model Context Protocol）的核心价值是标准化工具描述和调用接口。如果引入，我会：①将现有工具注册中心改造为 MCP Server，每个工具提供标准的 JSON Schema 描述；②Orchestrator 作为 MCP Client，通过标准协议发现和调用工具；③好处是工具可以跨 Agent 框架复用，且支持动态工具发现。但需要评估引入 MCP 的额外复杂度是否值得——目前项目工具数量有限且变动不频繁，自建注册中心已经够用。
