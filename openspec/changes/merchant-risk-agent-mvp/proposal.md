## Why

平台商家在经营中频繁遇到"退货激增 → 运费险/退款支出增加 → 回款延迟 → 短期现金流缺口"的连锁风险，当前数据散落在订单、退货、物流、回款、保险、融资多个系统，运营人员只能查看静态报表，无法快速判断未来 14 天是否会出现资金断流，理赔/授信/回款/保险调整各自独立缺少统一动作建议，每次人工归因和整理材料效率极低且缺少审计留痕。需要构建一个面向内部运营人员的案件工作台 MVP，实现"自动发现高风险商家 → 自动归因 → 预测现金缺口 → 推荐处置动作 → 人工审批 → 审计留痕"的完整闭环。

## What Changes

- 新建 monorepo 项目骨架（前端 Next.js + TypeScript + Tailwind，后端 FastAPI，数据库 SQLite）
- 创建完整数据库 schema（merchants、orders、returns、logistics_events、settlements、insurance_policies、financing_products、risk_cases、evidence_items、recommendations、reviews、audit_logs 共 12 张表）
- 实现 mock 数据生成器（50 个商家、90 天经营数据、覆盖高退货+回款延迟/高退货但现金充足/疑似异常退货 3 类风险场景）
- 实现风险案件自动生成脚本（基于退货率放大倍数、预测现金缺口、回款延迟、异常退货信号等规则）
- 实现数值分析引擎（7 日退货率、28 日基线退货率、退货率放大倍数、平均回款延迟天数、退款压力、14 日现金缺口预测、异常退货分数，所有数值由 Python 函数计算，不允许由 LLM 生成）
- 实现 14 日现金缺口预测（滚动均值 + 简单季节性系数 + 已知应收/应付计划）
- 构建 Agent 编排层（Orchestrator + 分析 Agent + 推荐 Agent + 证据 Agent + 守卫规则引擎，第一阶段先用 mock Agent 响应）
- 构建风险看板页面（顶部指标卡 + 筛选区 + 案件列表，支持排序/筛选/搜索）
- 构建案件详情页（商家信息 + 趋势图 + 风险评分拆解 + 14 日现金流预测图 + Agent 摘要 + 根因 + 动作建议 + 证据链时间线）
- 实现审批流与审计日志（NEW → ANALYZED → PENDING_REVIEW → APPROVED/REJECTED 状态流转，修改/驳回需填理由，完整审计记录）
- 实现案件导出（Markdown / JSON 格式）
- 实现 RESTful API 层（案件列表、详情、重新分析、证据获取、审批、导出）

## Capabilities

### New Capabilities
- `database-schema`: 数据库建模与迁移，定义 12 张核心业务表的结构、关系与索引
- `mock-data-generator`: Mock 数据生成器，产生 50 个商家 90 天经营数据覆盖 3 类风险场景
- `risk-case-engine`: 风险案件自动生成引擎，基于业务规则扫描商家数据并创建风险案件
- `metrics-engine`: 数值分析引擎，计算 7 日退货率、基线退货率、退款压力、异常退货分数等核心指标
- `cashflow-forecast`: 14 日现金缺口预测，基于滚动均值和季节性系数输出每日净现金流与累计缺口
- `agent-orchestrator`: Agent 编排层，协调分析/推荐/证据/守卫四个逻辑子 Agent 生成案件摘要与动作建议
- `risk-dashboard`: 风险看板前端页面，展示指标卡、筛选区和案件列表
- `case-detail-page`: 案件详情前端页面，展示趋势图、预测图、Agent 摘要、建议和证据链
- `approval-workflow`: 审批流与审计日志，支持案件审批状态流转和完整操作记录
- `case-export`: 案件导出功能，支持 Markdown 和 JSON 格式
- `rest-api`: RESTful API 层，提供案件列表/详情/分析/证据/审批/导出等接口

### Modified Capabilities

（无，这是全新项目）

## Impact

- **代码**：新建完整 monorepo，包含 `frontend/`（Next.js）和 `backend/`（FastAPI）两个子项目
- **API**：新增 7 个 REST 端点（GET/POST /api/risk-cases 系列）
- **数据库**：新建 SQLite 数据库，含 12 张表和相关索引
- **依赖**：后端依赖 FastAPI、SQLAlchemy、Pydantic、uvicorn；前端依赖 Next.js、TypeScript、Tailwind CSS、Recharts/ECharts
- **部署**：本地开发环境运行，无需外部服务依赖（第一阶段使用 mock Agent 响应，不对接真实 LLM 服务）
