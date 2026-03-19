## 1. 数据库模型扩展

- [ ] 1.1 在 `backend/app/models/models.py` 新增 WorkflowRun 模型（id, case_id, graph_version, status, current_node, started_at, updated_at, paused_at, resumed_at, ended_at）
- [ ] 1.2 在 `backend/app/models/models.py` 新增 AgentRun 模型（id, workflow_run_id, agent_name, model_name, prompt_version, schema_version, input_json, output_json, status, latency_ms, created_at）
- [ ] 1.3 在 `backend/app/models/models.py` 新增 Checkpoint 模型（id, workflow_run_id, node_name, checkpoint_blob, created_at）
- [ ] 1.4 在 `backend/app/models/models.py` 新增 ApprovalTask 模型（id, workflow_run_id, case_id, approval_type, assignee_role, status, payload_json, reviewer, reviewed_at, comment, final_action_json, created_at, due_at）
- [ ] 1.5 在 `backend/app/models/models.py` 新增 ToolInvocation 模型（id, workflow_run_id, tool_name, tool_version, input_json, output_json, approval_required, approval_status, status, idempotency_key, created_at）
- [ ] 1.6 在 `backend/app/models/models.py` 新增 PromptVersion 模型（id, agent_name, version, content, status, created_at）
- [ ] 1.7 在 `backend/app/models/models.py` 新增 SchemaVersion 模型（id, agent_name, version, json_schema, created_at）
- [ ] 1.8 在 `backend/app/models/models.py` 新增 EvalDataset、EvalRun、EvalResult 模型
- [ ] 1.9 更新 `backend/app/models/__init__.py` 导出新增模型
- [ ] 1.10 更新 mock 数据生成脚本 `backend/scripts/generate_mock_data.py` 建表逻辑，确保新表自动创建

## 2. Agent 输入输出契约（Pydantic Schemas）

- [ ] 2.1 在 `backend/app/agents/schemas.py` 定义 AgentInput 通用输入 schema（case_id, merchant_id, state_version, trigger_type, context_refs, policy_version）
- [ ] 2.2 定义 TriageOutput schema（case_type, priority, recommended_path）
- [ ] 2.3 定义 DiagnosisOutput schema（root_causes, business_summary, key_factors）
- [ ] 2.4 定义 ForecastOutput schema（daily_forecasts, gap_amount, min_cash_point, confidence_interval）
- [ ] 2.5 定义 RecommendationOutput schema（risk_level, recommendations 列表）
- [ ] 2.6 定义 EvidenceOutput schema（evidence_bundle, coverage_summary）
- [ ] 2.7 定义 GuardOutput schema（passed, reason_codes, blocked_actions, next_state）
- [ ] 2.8 定义 SummaryOutput schema（case_summary, action_results, final_status）
- [ ] 2.9 定义 WorkflowState TypedDict 作为 LangGraph graph state

## 3. 新增 Specialist Agent

- [ ] 3.1 创建 `backend/app/agents/triage_agent.py` — TriageAgent，根据案件上下文判断 case_type 和 priority
- [ ] 3.2 创建 `backend/app/agents/compliance_agent.py` — ComplianceGuardAgent，校验是否越权/命中审批规则/schema 校验/敏感词/禁止结论
- [ ] 3.3 创建 `backend/app/agents/execution_agent.py` — ExecutionAgent，审批通过后调用工具/连接器执行动作
- [ ] 3.4 创建 `backend/app/agents/summary_agent.py` — SummaryAgent，生成最终案件摘要
- [ ] 3.5 适配现有 `analysis_agent.py` 为 DiagnosisAgent 接口，输入输出对齐 AgentInput/DiagnosisOutput
- [ ] 3.6 适配现有 `recommend_agent.py` 输入输出对齐 AgentInput/RecommendationOutput
- [ ] 3.7 适配现有 `evidence_agent.py` 输入输出对齐 AgentInput/EvidenceOutput
- [ ] 3.8 适配现有 `guardrail.py` 为 GuardOutput 输出格式

## 4. LangGraph 工作流引擎

- [ ] 4.1 新增 `backend/app/workflow/` 目录，创建 `__init__.py`
- [ ] 4.2 创建 `backend/app/workflow/state.py` 定义 WorkflowState TypedDict 和状态枚举（WorkflowStatus）
- [ ] 4.3 创建 `backend/app/workflow/nodes.py` 实现 14 个 graph 节点函数（load_case_context, triage_case, compute_metrics, forecast_gap, diagnose_case, collect_evidence, generate_recommendations, run_guardrails, create_approval_tasks, wait_for_approval, execute_actions, wait_external_callback, finalize_summary, write_audit_log）
- [ ] 4.4 创建 `backend/app/workflow/graph.py` 使用 LangGraph StateGraph 构建主流程图，定义节点连接和条件分支路由
- [ ] 4.5 实现条件分支路由函数：根据 triage 输出的 case_type 决定走哪条子路径
- [ ] 4.6 集成 langgraph-checkpoint-sqlite 实现 checkpoint 持久化
- [ ] 4.7 实现 graph 编译和启动入口函数 `start_workflow(case_id)` 和 `resume_workflow(run_id)`

## 5. 失败回退与重试机制

- [ ] 5.1 创建 `backend/app/workflow/retry.py` 实现三级降级策略（L1 自动重试 + L2 规则降级 + L3 人工接管）
- [ ] 5.2 在每个 LLM 节点中集成重试装饰器，支持最多 3 次指数退避重试
- [ ] 5.3 实现 LLM 节点降级到 `engine/rules.py` 的 fallback 路径
- [ ] 5.4 实现人工接管任务创建逻辑，workflow 进入 PAUSED 状态
- [ ] 5.5 实现手动重试入口：从 checkpoint 恢复并从失败节点重新执行

## 6. 审批中心后端

- [ ] 6.1 创建 `backend/app/schemas/approval_schemas.py` 定义审批相关 Pydantic schemas（ApprovalTaskResponse, ApproveRequest, RejectRequest, ReviseAndApproveRequest）
- [ ] 6.2 创建 `backend/app/api/approvals.py` 实现审批 API（GET 列表, GET 详情, POST approve, POST reject, POST revise-and-approve）
- [ ] 6.3 实现审批通过后自动触发 workflow resume 逻辑
- [ ] 6.4 实现审批驳回后 workflow 进入 REJECTED 状态逻辑
- [ ] 6.5 实现批量审批接口（POST /api/approvals/batch）
- [ ] 6.6 实现 SLA 超时标记逻辑（due_at 过期后标记为 OVERDUE）

## 7. 工具注册与连接器

- [ ] 7.1 创建 `backend/app/services/tool_registry.py` 实现工具注册中心，维护工具元数据（name, version, approval_policy）
- [ ] 7.2 实现工具调用日志记录，每次调用写入 tool_invocations 表
- [ ] 7.3 实现幂等键生成和防重逻辑
- [ ] 7.4 实现审批前置拦截：approval_policy=REQUIRED 的工具需先创建审批任务
- [ ] 7.5 创建至少 2 个 mock 连接器（1 个读：query_credit_score，1 个写：submit_advance_settlement）

## 8. 版本管理后端

- [ ] 8.1 创建 `backend/app/api/configs.py` 实现配置管理 API（GET agent-configs, POST prompt-versions, POST schema-versions, POST model-policies）
- [ ] 8.2 实现 prompt 版本 CRUD + 激活/归档/回滚逻辑
- [ ] 8.3 实现 schema 版本 CRUD 逻辑
- [ ] 8.4 实现灰度开关：按比例分配流量到新旧版本
- [ ] 8.5 确保每次 agent_run 记录绑定 prompt_version 和 schema_version

## 9. 评测中心后端

- [ ] 9.1 创建 `backend/app/api/evals.py` 实现评测 API（POST datasets, POST runs, GET runs/{id}）
- [ ] 9.2 实现离线评测运行逻辑：逐条执行测试案例并记录结果
- [ ] 9.3 实现评测指标计算：采纳率、回退率、证据覆盖率、schema 合格率
- [ ] 9.4 实现线上抽样逻辑：从 agent_runs 中随机抽样
- [ ] 9.5 实现幻觉率检测：检查输出是否有 evidence_ids 支撑

## 10. RBAC 权限控制

- [ ] 10.1 创建 `backend/app/core/rbac.py` 定义 5 种角色和权限矩阵
- [ ] 10.2 创建 `backend/app/core/auth_middleware.py` 实现 FastAPI 中间件，在请求级别校验角色权限
- [ ] 10.3 为所有新增 API 端点添加角色权限装饰器
- [ ] 10.4 实现未认证返回 401、权限不足返回 403 的标准错误处理

## 11. Workflow 管理 API

- [ ] 11.1 创建 `backend/app/api/workflows.py` 实现 POST /api/workflows/start（启动新 workflow）
- [ ] 11.2 实现 POST /api/workflows/{run_id}/resume（恢复暂停 workflow）
- [ ] 11.3 实现 POST /api/workflows/{run_id}/retry（重试失败 workflow）
- [ ] 11.4 实现 GET /api/workflows/{run_id}（获取 workflow 详情）
- [ ] 11.5 实现 GET /api/workflows/{run_id}/trace（获取执行轨迹，含每个节点的 agent_runs）
- [ ] 11.6 实现 GET /api/cases/{case_id}/latest-run（获取最新 workflow run）
- [ ] 11.7 实现 POST /api/cases/{case_id}/reopen（重开案件，创建新 workflow_run）
- [ ] 11.8 在 `backend/app/main.py` 注册 workflows、approvals、configs、evals 四个 router

## 12. 前端类型与 API 客户端

- [ ] 12.1 在 `frontend/src/types/index.ts` 新增 WorkflowRun、AgentRun、ApprovalTask、ToolInvocation、PromptVersion、SchemaVersion、EvalDataset、EvalRun 类型定义
- [ ] 12.2 在 `frontend/src/lib/api.ts` 新增 workflow 相关 API 调用函数（startWorkflow, resumeWorkflow, retryWorkflow, getWorkflowRun, getWorkflowTrace, getLatestRun, reopenCase）
- [ ] 12.3 新增审批 API 调用函数（getApprovals, getApprovalDetail, approveTask, rejectTask, reviseAndApprove, batchApprove）
- [ ] 12.4 新增配置 API 调用函数（getAgentConfigs, createPromptVersion, createSchemaVersion, createModelPolicy）
- [ ] 12.5 新增评测 API 调用函数（createEvalDataset, createEvalRun, getEvalRun）

## 13. 审批中心前端页面

- [ ] 13.1 创建 `frontend/src/app/approvals/page.tsx` 审批列表页，支持按状态和类型筛选，显示 SLA 倒计时
- [ ] 13.2 创建 `frontend/src/app/approvals/[id]/page.tsx` 审批详情页，展示审批内容、证据链、操作按钮（批准/驳回/修改后批准）
- [ ] 13.3 实现批量审批功能（勾选多个任务 + 批量操作栏）
- [ ] 13.4 实现 SLA 超时高亮样式

## 14. 工作流运行中心前端页面

- [ ] 14.1 创建 `frontend/src/app/workflows/page.tsx` workflow 列表页，支持按 status 和 case_id 筛选
- [ ] 14.2 创建 `frontend/src/app/workflows/[id]/page.tsx` workflow 详情页，展示节点执行时间线
- [ ] 14.3 实现节点耗时可视化（水平时间线或瀑布图）
- [ ] 14.4 实现失败节点高亮和错误信息展示
- [ ] 14.5 实现"重试"和"恢复"操作按钮

## 15. 设置中心与评测中心前端页面

- [ ] 15.1 创建 `frontend/src/app/settings/page.tsx` 设置中心，含 Prompt 版本、Schema 版本、模型策略、工具配置、审批规则 5 个 Tab
- [ ] 15.2 实现 Prompt 版本列表 + 创建/激活/归档操作
- [ ] 15.3 实现模型策略配置界面
- [ ] 15.4 创建 `frontend/src/app/evals/page.tsx` 评测中心，展示数据集列表和评测运行结果
- [ ] 15.5 实现评测结果展示（采纳率、回退率、证据覆盖率、schema 合格率图表）

## 16. 风险指挥台与案件工作台升级

- [ ] 16.1 升级 `frontend/src/app/page.tsx` 风险看板为指挥台：新增待审批快捷入口、失败工作流入口、处理中案件统计
- [ ] 16.2 升级 `frontend/src/app/cases/[id]/page.tsx` 案件详情页：新增子 Agent 输出折叠区，展示每个 Agent 的输入输出
- [ ] 16.3 在案件详情页增加 workflow 状态展示（当前节点、执行进度）
- [ ] 16.4 更新 `frontend/src/app/layout.tsx` 导航栏，新增审批中心、工作流、设置、评测 4 个菜单入口

## 17. 依赖与集成

- [ ] 17.1 在 `backend/requirements.txt` 新增 langgraph 和 langgraph-checkpoint-sqlite 依赖
- [ ] 17.2 重构 `backend/app/agents/orchestrator.py`，将 run_full_analysis() 替换为 graph.invoke() 调用，保留旧逻辑作为 fallback
- [ ] 17.3 更新 `backend/app/services/approval.py`，审批通过后触发 workflow resume（而非仅触发 task_generator）
- [ ] 17.4 更新 mock 数据生成脚本，生成 workflow_runs、agent_runs、approval_tasks 测试数据
- [ ] 17.5 端到端冒烟测试：从案件创建 → workflow 启动 → Agent 逐节点执行 → 审批 → 执行 → 完成 的完整流程验证
