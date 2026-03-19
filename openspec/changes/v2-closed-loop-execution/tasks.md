## 1. 数据库模型扩展

- [x] 1.1 新增 `FinancingApplication` 模型（financing_applications 表），包含 id、merchant_id、case_id、recommendation_id、amount_requested、loan_purpose、repayment_plan_json、merchant_info_snapshot_json、historical_settlement_json、approval_status、reviewer_comment、created_at、updated_at
- [x] 1.2 新增 `Claim` 模型（claims 表），包含 id、merchant_id、case_id、recommendation_id、policy_id、claim_amount、claim_reason、evidence_snapshot_json、return_details_json、claim_status、reviewer_comment、created_at、updated_at
- [x] 1.3 新增 `ManualReview` 模型（manual_reviews 表），包含 id、merchant_id、case_id、recommendation_id、task_type、review_reason、evidence_ids_json、assigned_to、status、review_result、reviewer_comment、created_at、updated_at、completed_at
- [x] 1.4 扩展 `Recommendation` 模型，新增 task_generated（Integer 0/1）、task_type（String）、task_id（Integer）字段
- [x] 1.5 扩展 `RiskCase` 模型，增加与 FinancingApplication、Claim、ManualReview 的 relationship
- [x] 1.6 新增状态枚举：TaskStatus（DRAFT/PENDING_REVIEW/APPROVED/REJECTED/EXECUTING/COMPLETED）、ReviewTaskStatus（PENDING/IN_PROGRESS/COMPLETED/CLOSED）
- [x] 1.7 运行数据库初始化脚本，验证新表创建成功

## 2. 规则引擎

- [x] 2.1 创建 `engine/rules.py`，定义融资资格判断函数 `check_financing_eligibility(db, merchant_id, predicted_gap) -> dict`
- [x] 2.2 实现融资资格判断逻辑：检查近 90 天销售额、退货率、回款延迟、店铺等级，返回 eligible + recommended_amount 或 rejection_reasons
- [x] 2.3 实现理赔条件匹配函数 `check_claim_eligibility(db, merchant_id, case_id) -> dict`，检查有效保单和退货金额
- [x] 2.4 实现复核触发条件评估函数 `check_review_trigger(db, merchant_id, case_id, agent_output) -> dict`，检查退货率放大倍数和高风险标记
- [x] 2.5 为规则引擎添加单元测试数据验证（使用现有 Mock 数据运行）

## 3. 任务生成引擎

- [x] 3.1 创建 `services/task_generator.py`，定义统一入口函数 `generate_tasks_for_case(db, case_id) -> list[dict]`
- [x] 3.2 实现融资申请草稿生成逻辑：调用规则引擎→填充商家快照→填充历史回款→创建 FinancingApplication 记录
- [x] 3.3 实现理赔申请草稿生成逻辑：调用规则引擎→匹配保单→填充退货详情→填充证据快照→创建 Claim 记录
- [x] 3.4 实现人工复核任务生成逻辑：调用规则引擎→收集证据 ID→创建 ManualReview 记录
- [x] 3.5 实现 Recommendation.task_generated 幂等检查，已生成则跳过
- [x] 3.6 实现审计日志记录：每个生成的任务都在 audit_logs 中写入记录
- [x] 3.7 运行任务生成引擎验证：对现有 Mock 案件生成执行任务，验证生成数量 >= 1

## 4. Orchestrator 编排层扩展

- [x] 4.1 修改 `agents/orchestrator.py`，在 Agent 分析完成后调用 `generate_tasks_for_case`
- [x] 4.2 在回退模式（_fallback_analysis）中也触发复核任务生成（高风险案件）

## 5. 审批服务扩展

- [x] 5.1 修改 `services/approval.py`，在审批通过（APPROVED）时自动调用 `generate_tasks_for_case` 对未生成任务的建议进行评估
- [x] 5.2 审批通过后在审计日志中记录"已触发执行任务生成"

## 6. Pydantic Schema 扩展

- [x] 6.1 新增 `FinancingApplicationResponse`、`FinancingApplicationCreate` Schema
- [x] 6.2 新增 `ClaimResponse`、`ClaimCreate` Schema
- [x] 6.3 新增 `ManualReviewResponse`、`ManualReviewCreate` Schema
- [x] 6.4 新增 `UnifiedTaskListItem` Schema（统一任务列表响应）
- [x] 6.5 新增 `TaskStatusUpdate` Schema（状态更新请求）

## 7. REST API — 任务生成端点

- [x] 7.1 实现 `POST /api/risk-cases/{case_id}/generate-financing-application`，手动触发融资申请生成
- [x] 7.2 实现 `POST /api/risk-cases/{case_id}/generate-claim-application`，手动触发理赔申请生成
- [x] 7.3 实现 `POST /api/risk-cases/{case_id}/generate-manual-review`，手动触发复核任务生成

## 8. REST API — 任务管理端点

- [x] 8.1 实现 `GET /api/tasks`，统一任务列表查询，支持 task_type/status/assigned_to 筛选 + 分页
- [x] 8.2 实现 `GET /api/tasks/{task_type}/{task_id}`，任务详情查询
- [x] 8.3 实现 `PUT /api/tasks/{task_type}/{task_id}/status`，任务状态更新，包含状态机合法性验证
- [x] 8.4 新增 `api/tasks.py` 路由文件并注册到 main.py
- [x] 8.5 实现 `GET /api/risk-cases/{case_id}/tasks`，查询案件关联的所有执行任务

## 9. Mock 数据更新

- [x] 9.1 扩展 `scripts/generate_risk_cases.py`，在生成风险案件后自动调用任务生成引擎
- [x] 9.2 验证 Mock 数据中至少生成 3 条融资申请、2 条理赔申请、3 条复核任务
- [x] 9.3 更新 `scripts/generate_mock_data.py`，为融资产品表添加 eligibility_rule_json 配置数据

## 10. 前端 — 任务管理看板页面

- [x] 10.1 创建 `/tasks` 页面路由文件 `frontend/src/app/tasks/page.tsx`
- [x] 10.2 实现看板三列布局：待处理/处理中/已完成
- [x] 10.3 实现任务卡片组件：展示任务类型图标、商家名称、状态标签、创建时间
- [x] 10.4 实现筛选栏：按类型（融资/理赔/复核）和负责人筛选
- [x] 10.5 实现任务卡片点击跳转到对应详情页
- [x] 10.6 实现 30 秒自动刷新

## 11. 前端 — 融资申请详情页

- [x] 11.1 创建 `/tasks/financing/[id]/page.tsx` 页面
- [x] 11.2 展示融资申请草稿内容：商家信息、资金需求、历史回款、还款计划
- [x] 11.3 实现"提交审核"和"审核通过/驳回"操作按钮

## 12. 前端 — 理赔申请详情页

- [x] 12.1 创建 `/tasks/claims/[id]/page.tsx` 页面
- [x] 12.2 展示理赔申请草稿内容：商家信息、退货详情、证据、保单信息
- [x] 12.3 实现"提交审核"和"审核通过/驳回"操作按钮

## 13. 前端 — 人工复核任务详情页

- [x] 13.1 创建 `/tasks/reviews/[id]/page.tsx` 页面
- [x] 13.2 展示复核任务内容：复核理由、关联证据、商家信息
- [x] 13.3 实现"领取任务"、"提交复核结果"操作
- [x] 13.4 复核结果表单：review_result 下拉选择 + reviewer_comment 文本输入

## 14. 前端 — 案件详情页扩展

- [x] 14.1 在案件详情页新增"执行任务"Tab
- [x] 14.2 Tab 内展示该案件关联的所有任务列表（类型、状态、创建时间）
- [x] 14.3 审批通过后在页面顶部显示"已自动生成 N 条执行任务"提示条
- [x] 14.4 导航栏新增"任务管理"入口链接

## 15. 前端 — TypeScript 类型和 API 客户端扩展

- [x] 15.1 在 `types/index.ts` 中新增 FinancingApplication、Claim、ManualReview、UnifiedTask 类型定义
- [x] 15.2 在 `lib/api.ts` 中新增任务相关 API 调用函数（getTasks、getTaskDetail、updateTaskStatus、generateFinancing、generateClaim、generateReview）

## 16. 集成验证

- [x] 16.1 启动后端，运行 Mock 数据生成 + 风险案件生成 + 任务生成，验证全流程
- [x] 16.2 通过 API 验证：案件分析→建议生成→任务自动生成→任务状态流转完整链路
- [x] 16.3 启动前端，验证任务管理看板页面、各类任务详情页、案件详情页执行任务 Tab 正常展示
