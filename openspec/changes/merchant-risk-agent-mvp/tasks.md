## 1. 项目骨架与基础工程

- [x] 1.1 创建 monorepo 目录结构：frontend/（Next.js）和 backend/（FastAPI），配置 .gitignore
- [x] 1.2 初始化后端 FastAPI 项目：创建 backend/app/ 目录结构（api/、models/、schemas/、services/、agents/、engine/、core/），编写 main.py 入口和 requirements.txt
- [x] 1.3 初始化前端 Next.js 项目：创建 frontend/ 并配置 TypeScript + Tailwind CSS + App Router，安装 Recharts 依赖
- [x] 1.4 配置后端 CORS 中间件，允许 localhost:3000 跨域访问
- [x] 1.5 配置后端 SQLite 数据库连接（SQLAlchemy），编写 core/database.py 和 core/config.py

## 2. 数据库 Schema

- [x] 2.1 创建 merchants 模型（id、name、industry、settlement_cycle_days、store_level、created_at）
- [x] 2.2 创建 orders 模型（id、merchant_id、sku_id、order_amount、order_time、delivered_time）
- [x] 2.3 创建 returns 模型（id、order_id、return_reason、return_time、refund_amount、status）
- [x] 2.4 创建 logistics_events 模型（id、order_id、event_type、event_time）
- [x] 2.5 创建 settlements 模型（id、merchant_id、expected_settlement_date、actual_settlement_date、amount、status）
- [x] 2.6 创建 insurance_policies 模型（id、merchant_id、policy_type、coverage_limit、premium_rate、status）
- [x] 2.7 创建 financing_products 模型（id、name、max_amount、eligibility_rule_json、status）
- [x] 2.8 创建 risk_cases 模型（id、merchant_id、risk_score、risk_level、trigger_json、status、agent_output_json、created_at、updated_at），status 支持 NEW/ANALYZED/PENDING_REVIEW/APPROVED/REJECTED 枚举
- [x] 2.9 创建 evidence_items 模型（id、case_id、evidence_type、source_table、source_id、summary、importance_score）
- [x] 2.10 创建 recommendations 模型（id、case_id、action_type、content_json、confidence、requires_manual_review）
- [x] 2.11 创建 reviews 模型（id、case_id、reviewer_id、decision、comment、final_action_json、created_at）
- [x] 2.12 创建 audit_logs 模型（id、entity_type、entity_id、actor、action、old_value、new_value、created_at）
- [x] 2.13 编写数据库初始化脚本，创建所有表和必要索引（risk_cases 的 merchant_id、status、risk_level）

## 3. Mock 数据生成器

- [x] 3.1 编写 scripts/generate_mock_data.py 主脚本框架，支持 seed 参数实现数据可重复
- [x] 3.2 生成 50 个商家记录，覆盖女装、数码、家居、食品、美妆等 5+ 行业，settlement_cycle_days 3-14 天随机，store_level 包含 gold/silver/bronze
- [x] 3.3 生成 90 天订单数据，每商家每日 5-50 笔订单
- [x] 3.4 生成退货数据，关联 orders 表，按 3 类风险场景分配退货率：场景 A（8-12 个商家，退货率 >= 20%）、场景 B（5-8 个商家，退货率 >= 18% 但回款正常）、场景 C（3-5 个商家，异常退货模式）
- [x] 3.5 生成物流事件数据（揽收、运输中、签收、退回等事件类型）
- [x] 3.6 生成回款数据，场景 A 商家设置 3+ 天延迟，场景 B 商家回款正常
- [x] 3.7 生成保险保单和融资产品基础数据
- [x] 3.8 验证数据生成脚本可正常运行，种子一致性测试

## 4. 数值分析引擎

- [x] 4.1 实现 compute_return_rate(merchant_id, days) — 计算指定天数退货率
- [x] 4.2 实现 compute_baseline_return_rate(merchant_id) — 计算 28 日基线退货率
- [x] 4.3 实现 compute_return_amplification(merchant_id) — 计算退货率放大倍数（含除零保护）
- [x] 4.4 实现 compute_avg_settlement_delay(merchant_id) — 计算近 30 天平均回款延迟
- [x] 4.5 实现 compute_refund_pressure(merchant_id, days) — 计算退款压力（退款总金额）
- [x] 4.6 实现 compute_anomaly_score(merchant_id) — 计算异常退货分数（0-1），基于同原因高频退货、签收后快速退款等信号
- [x] 4.7 编写数值分析引擎的单元测试

## 5. 14 日现金缺口预测

- [x] 5.1 实现 forecast_cash_gap(merchant_id, horizon_days=14) — 滚动均值 + 周几季节性系数 + 已知应收/应付计划
- [x] 5.2 输出每日 inflow/outflow/netflow 数组、predicted_gap、lowest_cash_day、confidence
- [x] 5.3 实现置信度计算（基于历史数据波动性/标准差）
- [x] 5.4 编写现金缺口预测的单元测试

## 6. 风险案件生成脚本

- [x] 6.1 实现风险案件生成逻辑：扫描所有商家，基于退货率放大倍数 >= 1.6、预测缺口 >= 50000、回款延迟 >= 3 天、异常分数 >= 0.8 四个触发条件
- [x] 6.2 实现风险等级自动评定（High/Medium/Low 规则）
- [x] 6.3 实现去重逻辑：同一商家同一天不重复生成案件
- [x] 6.4 实现批量扫描执行入口 scripts/generate_risk_cases.py
- [x] 6.5 验证运行后可生成至少 5 条有效案件

## 7. Agent 编排层（Mock 实现）

- [x] 7.1 实现 Orchestrator.analyze(case_id) 主函数，编排指标计算→证据收集→摘要生成→建议生成→守卫校验的流程
- [x] 7.2 实现 EvidenceAgent（mock）：为案件收集证据，生成 evidence_id 映射，确保每条建议至少挂 1 条证据
- [x] 7.3 实现 AnalysisAgent（mock）：基于规则生成案件摘要 JSON，包含 risk_level、case_summary、root_causes、manual_review_required
- [x] 7.4 实现 RecommendAgent（mock）：根据案件指标生成动作建议（回款加速/经营贷/运费险调整/异常退货复核），包含经营贷资格检查（经营历史 >= 60 天等）
- [x] 7.5 实现 GuardrailEngine：JSON Schema 校验、融资/反欺诈类 requires_manual_review=true 检查、禁止性结论拦截
- [x] 7.6 实现分析失败回退逻辑：异常时回退到"结构化指标 + 规则建议"模式
- [x] 7.7 定义 Agent 输出 JSON Schema（Pydantic 模型），用于校验

## 8. REST API 层

- [x] 8.1 实现 GET /api/risk-cases — 案件列表（支持 risk_level、status、merchant_name、page、page_size 参数）
- [x] 8.2 实现 GET /api/risk-cases/{case_id} — 案件详情（含商家信息、指标、趋势数据、Agent 摘要、建议、证据、审计记录）
- [x] 8.3 实现 POST /api/risk-cases/{case_id}/analyze — 触发重新分析
- [x] 8.4 实现 GET /api/risk-cases/{case_id}/evidence — 获取证据列表
- [x] 8.5 实现 POST /api/risk-cases/{case_id}/review — 审批案件（含驳回必须填理由、融资类强制备注校验）
- [x] 8.6 实现 GET /api/risk-cases/{case_id}/export?format=markdown|json — 导出案件
- [x] 8.7 实现 GET /api/dashboard/stats — 看板顶部指标卡数据
- [x] 8.8 实现 Pydantic 请求/响应 Schema 定义

## 9. 审批流与审计日志服务

- [x] 9.1 实现审批服务：状态流转校验（NEW→ANALYZED→PENDING_REVIEW→APPROVED/REJECTED）
- [x] 9.2 实现审计日志服务：每次关键操作自动写入 audit_logs 表
- [x] 9.3 确保原始 Agent 输出不可覆盖，修改结果保存在 reviews.final_action_json

## 10. 前端 — 风险看板页面

- [x] 10.1 创建看板页面布局（/app/page.tsx），包含顶部指标卡区、筛选区、案件列表区
- [x] 10.2 实现顶部 4 个指标卡组件（监控商家数、新增高风险案件数、预计总缺口、平均回款延迟）
- [x] 10.3 实现筛选区组件（风险等级、行业、回款周期下拉选择，日期范围选择器）
- [x] 10.4 实现案件列表表格组件（商家名称、行业、7 日退货率、基线退货率、放大倍数、预测缺口、风险等级标签、建议动作数、状态、更新时间）
- [x] 10.5 实现列表排序功能（按预测缺口、风险等级、更新时间排序）
- [x] 10.6 实现点击行跳转详情页导航
- [x] 10.7 实现"重新分析"按钮交互
- [x] 10.8 实现 API 客户端 lib/api.ts（封装所有后端 API 调用）

## 11. 前端 — 案件详情页

- [x] 11.1 创建案件详情页布局（/app/cases/[id]/page.tsx），左右分栏 + 底部区域
- [x] 11.2 实现左侧商家基本信息卡片
- [x] 11.3 实现左侧 30 天趋势图（Recharts 折线图：订单金额、退货率、退款金额、回款金额）
- [x] 11.4 实现左侧风险评分拆解组件
- [x] 11.5 实现左侧 14 日现金流预测图（Recharts：inflow/outflow/netflow + 最低现金点标记）
- [x] 11.6 实现右侧 Agent 案件总结展示（风险等级标签 + 摘要文本 + 根因列表）
- [x] 11.7 实现右侧动作建议列表卡片（标题、原因、预期收益、置信度、人工复核标签）
- [x] 11.8 实现右侧证据引用展开交互（点击 evidence_id 展开原始数据）
- [x] 11.9 实现底部证据链时间线组件
- [x] 11.10 实现底部原始记录表格（订单、退货、回款等，支持分页）
- [x] 11.11 实现底部审计记录列表

## 12. 前端 — 审批抽屉

- [x] 12.1 实现审批 Drawer 组件（右侧滑出），展示 Agent 原始建议
- [x] 12.2 实现审批选项（批准/修改后批准/驳回）和备注输入
- [x] 12.3 实现驳回必须填理由、融资类动作强制备注的前端校验
- [x] 12.4 对接审批 API，提交后刷新详情页数据

## 13. 前端 — 导出功能

- [x] 13.1 实现导出按钮和格式选择（Markdown / JSON）
- [x] 13.2 对接导出 API，触发文件下载

## 14. 集成验证

- [x] 14.1 端到端验证场景 A：高退货 + 回款延迟 → 生成 High 案件 → 显示 14 日缺口 → 推荐回款加速 + SKU 策略调整
- [x] 14.2 端到端验证场景 B：高退货但现金充足 → 生成 Medium 案件 → 不推荐经营贷 → 推荐运费险策略调整
- [x] 14.3 端到端验证场景 C：疑似异常退货 → 输出人工复核建议 → requires_manual_review=true → 证据链有异常规则命中
- [x] 14.4 验证审批流程完整性：从 NEW → ANALYZED → PENDING_REVIEW → APPROVED，审计日志完整
- [x] 14.5 验证导出功能：Markdown 和 JSON 格式内容完整
