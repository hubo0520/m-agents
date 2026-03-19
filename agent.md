1. 文档信息

产品名称：商家经营保障 Agent V1
版本：0.1
阶段：阶段 1 / 单场景 MVP
产品形态：内部运营 Web 系统
语言：中文
默认数据源：Mock 数据 + 本地数据库
默认角色：风险运营、融资运营、管理员

2. 产品背景

平台商家在经营中会遇到一类典型问题：
退货突然升高 → 运费险/退款支出增加 → 回款未及时到账 → 形成短期现金流缺口。

传统处理方式的问题：

数据散落在订单、退货、物流、回款、保险、融资多个系统

运营同学只能看静态报表，无法快速判断未来 14 天是否会断流

理赔、授信、回款、保险调整是分开的，缺少统一动作建议

每次人工做归因和整理材料都很慢

决策过程缺少证据链和审计留痕

3. 产品目标
3.1 核心目标

给运营人员一个可执行的案件工作台，完成以下闭环：

自动发现高风险商家案件

自动解释“为什么有风险”

自动预测未来 14 天现金缺口

自动推荐处置动作

支持人工审批与修改

保存完整审计记录

3.2 非目标

第一阶段不做：

自动放款

自动拒赔

自动修改保险定价

真实支付/理赔系统对接

商家端自助提交

多场景覆盖

4. 目标用户
4.1 风险运营

关注：

哪些商家需要优先处理

风险原因是什么

是否有欺诈或异常退货迹象

4.2 融资运营

关注：

哪些商家有短期资金缺口

是否适合推荐回款加速/经营贷

需要哪些材料支持建议

4.3 管理员

关注：

风险阈值配置

产品规则配置

用户权限与审计

5. 核心场景

某女装商家近 7 天退货率从 12% 升到 24%，平均回款延迟 3 天。
系统检测到该商家未来 14 天将出现 8.6 万元现金缺口，并发现 3 笔退款存在异常模式。
Agent 给出建议：

建议发起 5 万元回款加速

建议对 2 个高退货 SKU 调整运费险策略

建议生成经营贷申请草稿

建议将 3 笔疑似异常退货转人工复核

运营人员审批后，系统导出案件摘要和证据清单。

6. 范围定义
6.1 In Scope（第一阶段必须做）

商家风险看板

风险案件自动生成

案件详情页

14 日现金缺口预测

Agent 归因总结

Agent 动作建议

证据链展示

人工审批流

审计日志

Markdown/JSON 导出

6.2 Should Have（有余力再做）

案件对话问答

推荐理由二次展开

简易产品规则后台

6.3 Out of Scope（阶段 1 不做）

真实授信申请提交

真实理赔申请提交

向量知识库

实时消息总线

手机端

7. 页面设计
7.1 页面一：风险看板

目标：让运营快速找到最值得处理的商家。

模块

顶部指标卡

监控商家数

今日新增高风险案件数

预计总现金缺口

平均回款延迟天数

筛选区

风险等级

行业

回款周期

是否有融资资格

日期范围

商家案件列表

商家名称

行业

7 日退货率

基线退货率

退货率放大倍数

14 日预测缺口

风险等级

建议动作数

案件状态

更新时间

交互

点击列表行进入案件详情

支持按“预测缺口”“风险等级”“更新时间”排序

支持“重新分析”按钮

7.2 页面二：案件详情页

目标：解释原因、展示预测、承载动作建议。

布局
左侧：

商家基本信息

最近 30 天趋势图

订单金额

退货率

退款金额

回款金额

风险评分拆解

14 日现金流预测图

右侧：

Agent 案件总结

根因列表

动作建议列表

人工复核标签

证据引用

底部：

证据链时间线

原始记录表格

审计记录

7.3 页面三：审批页 / 审批抽屉

目标：让运营确认或修改建议。

能力

查看 Agent 原始建议

选择“批准 / 修改后批准 / 驳回”

填写审批意见

对融资类、反欺诈类动作强制要求备注

保存最终动作结果

7.4 页面四：导出页

目标：生成可发给内部同事或进入下一系统的案件摘要。

导出内容

商家概况

风险结论

14 日缺口

动作建议

证据列表

审批记录

导出格式

Markdown

JSON

8. 功能需求
FR-001 风险案件自动生成

描述
系统按日扫描商家经营数据，生成风险案件。

输入

商家订单数据

退货数据

物流数据

回款数据

输出

风险案件记录

规则 v0
满足以下任一条件则生成案件：

7 日退货率 / 28 日基线退货率 >= 1.6

14 日预测现金缺口 >= 50,000

平均回款延迟天数 >= 3

疑似异常退货信号 >= 阈值

验收

跑一次任务后可生成至少 5 条有效案件

每条案件可关联到至少 1 个商家和一组原始记录

FR-002 风险看板

描述
展示风险案件列表与关键指标。

验收

支持筛选、排序、搜索

列表点击后进入详情页

页面首屏加载成功

FR-003 数值分析引擎

描述
生成结构化指标，供 Agent 和页面共同使用。

必须输出

7 日退货率

28 日基线退货率

退货率放大倍数

平均回款延迟天数

7/14 日退款压力

14 日预测现金缺口

疑似异常退货分数

约束

数值由后端函数生成，不允许由 LLM 直接编造

FR-004 Agent 案件总结

描述
Agent 读取结构化指标和证据，生成面向运营的自然语言总结。

输出要求

风险等级

1 段摘要

3 条以内核心成因

关键数字

需要人工复核的原因

示例
“该商家近 7 日退货率显著高于近 28 日基线，且回款延迟扩大，预计未来 14 日存在较大现金流缺口。建议优先处理回款加速，并对高退货 SKU 做策略调整。”

约束

所有数字必须引用结构化结果

所有结论必须引用 evidence_id

不允许输出“建议直接放款/拒赔”

FR-005 14 日现金缺口预测

描述
给出未来 14 天每日净现金流曲线和累计缺口。

v0 实现

用滚动均值 + 简单季节性系数 + 已知应收/应付计划

不做机器学习训练

输出

每日 inflow / outflow / netflow

最低现金点

累计缺口金额

置信度分数

验收

详情页能看到预测图

数值与源数据一致

预测函数可单元测试

FR-006 动作建议生成

描述
根据案件情况，Agent 给出处置动作。

动作类型

回款加速建议

经营贷建议

运费险策略调整建议

异常退货人工复核建议

每条建议必须包含

action_type

title

why

expected_benefit

confidence

evidence_ids

requires_manual_review

规则

涉及融资、反欺诈的动作必须 requires_manual_review = true

不满足资格约束时，不得推荐经营贷

FR-007 证据链展示

描述
每条成因、每条建议都能追溯到证据。

证据类型

订单

退货

物流轨迹

回款记录

规则命中

产品匹配结果

交互

点击 evidence_id 可展开原始数据

支持按时间线查看

验收

每条建议至少挂 1 条证据

每条核心成因至少挂 2 条证据或 1 条规则命中

FR-008 人工审批与修改

描述
运营人员可以审批、修改、驳回 Agent 建议。

状态流转

NEW

ANALYZED

PENDING_REVIEW

APPROVED

REJECTED

规则

修改或驳回必须填写理由

审批后生成最终动作快照

原始 Agent 输出不可覆盖，只能新增版本

FR-009 案件问答（可选）

描述
运营可以围绕当前案件提问。

示例问题

为什么推荐经营贷而不是只做回款加速？

哪几个 SKU 导致退货压力最高？

哪些证据支持“异常退货复核”？

约束

仅允许回答当前案件上下文

答案必须引用 evidence_id

不允许脱离案件数据自由发挥

FR-010 导出案件摘要

描述
导出用于内部流转的案件包。

内容

商家信息

风险摘要

现金缺口

建议动作

证据清单

审批记录

9. Agent 设计

第一阶段代码上不要真的上复杂分布式多 Agent，而是做成：

一个 Orchestrator + 四个逻辑子 Agent

9.1 风险监控 Agent（可先不用 LLM）

职责：

扫描商家

计算指标

生成案件

9.2 分析 Agent

职责：

读取案件上下文

总结风险原因

生成运营可读摘要

9.3 推荐 Agent

职责：

结合产品规则与资格约束

输出动作建议

9.4 证据 Agent

职责：

收集支撑每条结论的证据

生成 evidence_id 映射

9.5 守卫规则引擎

职责：

检查是否触发人工复核

拦截违规结论

校验 JSON 输出

9.6 Agent 工作流

定时任务生成案件

Orchestrator 读取案件

调用指标工具和证据工具

分析 Agent 输出摘要

推荐 Agent 输出动作

守卫规则引擎校验

保存到数据库

进入人工审批

9.7 工具列表

get_case_context(case_id)

get_merchant_metrics(merchant_id, days)

forecast_cash_gap(merchant_id, horizon_days)

retrieve_evidence(case_id)

match_financing_products(merchant_id, gap_amount)

check_guardrails(recommendations)

9.8 Agent 输出 JSON 规范
{
  "case_id": "RC-0001",
  "risk_level": "high",
  "case_summary": "近7日退货率显著高于基线，且回款延迟扩大，预计未来14日出现现金流缺口。",
  "root_causes": [
    {
      "label": "退货率异常上升",
      "explanation": "近7日退货率24%，高于28日基线12%。",
      "confidence": 0.91,
      "evidence_ids": ["EV-101", "EV-102"]
    }
  ],
  "cash_gap_forecast": {
    "horizon_days": 14,
    "predicted_gap": 86000,
    "lowest_cash_day": "2026-03-24",
    "confidence": 0.78
  },
  "recommendations": [
    {
      "action_type": "advance_settlement",
      "title": "建议优先发起回款加速",
      "why": "预计14日内出现较大缺口，且商家历史回款稳定。",
      "expected_benefit": "缓解短期流动性压力",
      "confidence": 0.82,
      "requires_manual_review": true,
      "evidence_ids": ["EV-201", "EV-202"]
    }
  ],
  "manual_review_required": true
}
10. 数据模型
10.1 merchants

id

name

industry

settlement_cycle_days

store_level

created_at

10.2 orders

id

merchant_id

sku_id

order_amount

order_time

delivered_time

10.3 returns

id

order_id

return_reason

return_time

refund_amount

status

10.4 logistics_events

id

order_id

event_type

event_time

10.5 settlements

id

merchant_id

expected_settlement_date

actual_settlement_date

amount

status

10.6 insurance_policies

id

merchant_id

policy_type

coverage_limit

premium_rate

status

10.7 financing_products

id

name

max_amount

eligibility_rule_json

status

10.8 risk_cases

id

merchant_id

risk_score

risk_level

trigger_json

status

created_at

10.9 evidence_items

id

case_id

evidence_type

source_table

source_id

summary

importance_score

10.10 recommendations

id

case_id

action_type

content_json

confidence

requires_manual_review

10.11 reviews

id

case_id

reviewer_id

decision

comment

final_action_json

created_at

10.12 audit_logs

id

entity_type

entity_id

actor

action

old_value

new_value

created_at

11. API 设计
11.1 获取案件列表

GET /api/risk-cases

参数：

risk_level

status

merchant_name

page

page_size

11.2 获取案件详情

GET /api/risk-cases/{case_id}

返回：

商家信息

核心指标

趋势图数据

Agent 摘要

建议列表

证据列表

审计记录

11.3 重新分析案件

POST /api/risk-cases/{case_id}/analyze

作用：

重新运行分析 Agent + 推荐 Agent

11.4 获取证据

GET /api/risk-cases/{case_id}/evidence

11.5 审批案件

POST /api/risk-cases/{case_id}/review

请求体：

{
  "decision": "approve",
  "comment": "同意先走回款加速，经营贷建议保留待人工电话核验后再提交。",
  "final_actions": []
}
11.6 导出案件

GET /api/risk-cases/{case_id}/export?format=markdown

11.7 可选：案件问答

POST /api/risk-cases/{case_id}/chat

请求体：

{
  "question": "为什么要建议经营贷？"
}
12. 业务规则 v0
12.1 风险等级

High：

退货率放大倍数 >= 1.6 且 14 日缺口 >= 50,000
或

疑似异常退货分数 >= 0.8

Medium：

退货率放大倍数 >= 1.3
或

平均回款延迟 >= 2 天

Low：其余

12.2 经营贷建议资格

满足以下条件才允许推荐：

店铺经营历史 >= 60 天

近 30 日严重争议率低于阈值

无高等级欺诈标记

预测缺口达到阈值

12.3 回款加速建议

触发条件：

预计未来 14 日缺口 > 0

有待结算金额

历史回款表现稳定

12.4 异常退货人工复核

触发条件示例：

同一地址/账号短期内高频退货

签收后极短时间退款异常集中

物流轨迹与退款行为冲突

说明
所有阈值都做成配置，不写死在页面里。

13. 非功能要求

所有 Agent 原始输出必须保留，不可覆盖

所有关键动作必须记录审计日志

地址、手机号等敏感信息默认脱敏

普通接口 P95 响应时间 < 1s

单次 Agent 分析目标 < 15s

Agent 输出必须通过 JSON Schema 校验

Agent 失败时页面回退到“结构化指标 + 规则建议”模式

不允许用户输入直接影响数值计算结果

14. 成功指标
14.1 业务指标

单案件平均处理时长下降

运营人工整理材料时间下降

建议采纳率

高风险案件首响时间下降

14.2 Agent 质量指标

建议证据覆盖率

JSON 输出成功率

幻觉率

人工改写率

14.3 系统指标

页面可用性

Agent 成功率

导出成功率

15. 验收场景
场景 A：高退货 + 回款延迟

预期：

生成 High 风险案件

显示 14 日现金缺口

推荐“回款加速 + SKU 策略调整”

场景 B：高退货但现金充足

预期：

生成 Medium 风险案件

不推荐经营贷

推荐“运费险策略调整”

场景 C：疑似异常退货

预期：

输出人工复核建议

requires_manual_review = true

证据链中可看到异常规则命中

16. 技术实现建议（给 AI coding 用）

推荐栈

前端：Next.js + TypeScript + Tailwind

后端：FastAPI

数据库：PostgreSQL

图表：ECharts 或 Recharts

Agent：Python Orchestrator + OpenAI 兼容接口

鉴权：最简 RBAC

明确取舍

第一阶段不要上向量库

第一阶段不要做真 ML 训练

第一阶段不要做复杂消息队列

先把 SQL、规则、证据链、审批流做好

原因很简单：第一阶段的数据主体是结构化经营数据，最核心的是“算得准、查得到、能审计”，不是“检索一堆文档”。

17. 给 AI coding 的拆任务顺序

不要一次性让 AI 生成全系统，按下面顺序喂：

建 monorepo 和基础工程

建数据库 schema 和 migration

写 mock 数据生成器

写风险案件生成脚本

做看板页

做案件详情页

做数值分析函数

接 Agent 摘要与建议输出

做审批流和审计日志

做导出功能

最后再补案件问答