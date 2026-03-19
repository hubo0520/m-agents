商家经营保障 Agent 系统级自测 PRD》
适用于你这套 多 Agent + 审批流 + 证据链 + 工作流恢复 + 连接器执行 的系统。
它不是测试用例清单，而是系统级自测产品文档，用于统一研发、测试、产品、算法、风控对“测什么、怎么测、测到什么程度才能上线”的理解。

商家经营保障 Agent
系统级自测 PRD

文档版本：v1.0
适用阶段：第三阶段 / 多 Agent + 生产化
文档类型：系统级自测 PRD
目标读者：产品经理、研发负责人、测试负责人、算法工程师、风控运营、合规
系统范围：风险识别、案件分析、推荐生成、证据绑定、审批流、执行流、审计与观测

1. 文档目标

本 PRD 用于定义系统级自测的目标、边界、范围、策略、验收标准与执行流程，确保系统在上线前具备以下能力：

功能正确

流程闭环

多 Agent 协同稳定

高风险动作可控

数据与证据可追溯

异常情况下可恢复

满足上线门禁

本 PRD 的重点不是验证单个页面或单个接口，而是验证整套系统在真实业务链路下是否能稳定完成“发现风险 -> 分析 -> 推荐 -> 审批 -> 执行/驳回 -> 留痕”的完整流程。

2. 背景与问题定义

随着系统从单点分析工具升级为多 Agent 生产化系统，风险也从“单功能 bug”升级为“系统协同失效”。
典型问题包括：

Agent 输出结构不稳定，导致后续节点失败

推荐有结论但无证据，无法审批

审批通过后工作流无法恢复

外部执行失败后状态错乱

规则引擎与 LLM 输出冲突

高风险动作绕过审批

服务重启后运行中的 workflow 丢失

模型升级后建议质量下降但未被发现

因此必须建立系统级自测机制，不仅验证局部功能，还要验证跨模块、跨状态、跨失败分支的全链路行为。

3. 自测目标
3.1 总体目标

在预发环境中，通过系统级自测覆盖核心业务路径、关键异常路径和上线门禁项，确保：

核心链路可跑通

关键节点可追踪

高风险动作不可失控

故障可回退

输出可审计

上线后具备可观测性

3.2 具体目标
功能目标

所有 P0 核心场景端到端可成功执行

所有高风险动作均经过审批

所有建议均有 evidence_ids

所有案件均可查看 trace、审批、导出、审计日志

稳定性目标

工作流支持暂停、恢复、重试

节点失败时可 fallback 或转人工

重启后运行状态不丢失

数据目标

系统计算结果与源数据一致

证据绑定正确

导出数据与页面展示一致

质量目标

Agent 输出 schema 合格率达标

幻觉率受控

审批驳回率在合理范围

建议覆盖率和证据覆盖率达标

4. 自测范围
4.1 In Scope

本次系统级自测覆盖以下模块：

A. 数据与案件生成层

数据导入

指标计算

风险案件生成

风险等级判定

案件版本管理

B. Agent 协同层

Triage Agent

Diagnosis Agent

Recommendation Agent

Evidence Agent

Guard Agent

Summary Agent

C. 工作流编排层

workflow start

条件分支

pause / resume

retry

failover

state persistence

checkpoint 恢复

D. 审批与执行层

待审批任务创建

审批通过 / 驳回 / 修改后批准

审批后恢复流程

执行动作创建

外部回调处理

失败重试与人工接管

E. 观测与审计层

audit logs

agent runs

workflow traces

tool invocation logs

approval logs

export logs

F. 用户界面层

风险指挥台

案件工作台

审批中心

运行中心

导出页

配置页关键只读项

4.2 Out of Scope

以下内容不在本次系统级自测 PRD 范围内：

单元测试细节

组件级视觉回归

第三方平台真实性能 SLA

正式生产压测结论

商家端 App 测试

全量历史数据迁移验证

5. 自测对象定义

系统级自测对象分为 6 类：

5.1 业务对象

merchant

order

return

settlement

insurance_policy

financing_product

risk_case

recommendation

review

audit_log

5.2 工作流对象

workflow_run

checkpoint

agent_run

approval_task

tool_invocation

callback_event

5.3 Agent 输出对象

case_summary

root_causes

risk_level

recommendations

evidence_bundle

guard_result

final_summary

5.4 页面对象

dashboard cards

case detail panels

approval detail

trace panel

evidence drawer

export preview

5.5 配置对象

prompt_version

schema_version

model_policy

approval_policy

guardrail_policy

risk_threshold

5.6 环境对象

app service

db

cache

queue / async worker

model gateway

connector mock service

observability service

6. 自测原则
原则 1：系统级优先验证完整闭环

优先验证端到端业务价值，而不是先验证局部技术细节。

原则 2：真实状态优先于 mock happy path

必须覆盖异常路径、审批驳回、工具失败、重试恢复、服务重启等场景。

原则 3：LLM 输出必须受约束验证

所有 Agent 输出都必须通过 schema 校验、证据校验、敏感动作校验。

原则 4：高风险动作默认从严验证

融资、反欺诈、理赔类动作必须验证“无法绕过审批”。

原则 5：结果必须可复盘

每次自测必须留下 run_id、case_id、trace、日志、结论与缺陷记录。

7. 自测场景分层

系统级自测按 5 层组织：

7.1 L1：冒烟层

验证系统是否“能跑起来”。

覆盖：

登录后可打开核心页面

可创建案件

可触发 workflow

可查看案件详情

可发起审批

可导出摘要

7.2 L2：核心业务闭环层

验证最核心业务路径。

覆盖：

高退货 + 回款延迟 -> 回款加速建议 -> 审批 -> 执行

高退货 + 现金缺口 -> 经营贷草稿 -> 审批 -> 生成材料

异常退货 -> 人工复核 -> 审批 -> 创建复核任务

理赔材料生成 -> 审批 -> 导出

7.3 L3：异常与守卫层

验证系统是否安全。

覆盖：

recommendation 无 evidence_ids

schema 不合法

输出命中禁止语义

高风险动作绕过审批

工具调用参数异常

外部回调重复到达

workflow 状态非法跳转

7.4 L4：恢复与韧性层

验证系统是否可恢复。

覆盖：

审批前 pause

审批后恢复

服务重启后恢复

执行失败后 retry

callback 超时

checkpoint 回放

fallback 到规则模式

7.5 L5：质量与门禁层

验证系统是否达到上线标准。

覆盖：

schema 合格率

建议证据覆盖率

trace 完整率

审批留痕完整率

导出一致性

核心接口性能

高优先级缺陷清零

8. 核心业务自测场景
场景 S1：高退货 + 回款延迟 + 现金缺口

目标：验证系统能生成高风险案件并推荐回款加速

输入条件

近 7 日退货率显著高于 28 日基线

待结算金额充足

平均回款延迟 >= 阈值

14 日预测现金流缺口 > 0

预期结果

生成 High 风险案件

Diagnosis Agent 输出根因

Recommendation Agent 输出 advance_settlement

recommendation 包含 evidence_ids

Guard Agent 判定需要审批

审批通过后恢复 workflow

创建执行任务

写入审计日志

场景 S2：高退货但现金充足

目标：验证系统不会过度推荐融资动作

输入条件

退货率异常

现金流充足

无明显待结算缺口

预期结果

案件等级 Medium

不推荐经营贷

推荐策略调整或人工关注

审批流可选或不触发

页面与导出结果一致

场景 S3：疑似异常退货

目标：验证欺诈 / 异常复核链路

输入条件

同地址高频退货

签收后极短时间退款

物流轨迹异常

预期结果

生成异常退货复核建议

requires_manual_review = true

未审批不可执行

审批通过后创建人工复核任务

evidence drawer 可展示命中记录

场景 S4：经营贷草稿生成

目标：验证资格规则 + 推荐约束

输入条件

经营历史达标

无高等级欺诈标记

缺口达到阈值

满足经营贷资格

预期结果

推荐 business_loan_draft

推荐理由与证据正确

高风险动作进入审批

审批后生成草稿，不直接提交真实放款

场景 S5：理赔材料生成

目标：验证证据编排和输出一致性

输入条件

保单存在

有符合规则的订单、物流、退款记录

预期结果

生成理赔材料草稿

证据来源正确

审批后可导出

审计日志完整

9. 异常与失败自测场景
F1：Agent 输出 schema 不合法

预期

节点失败

Guard 阻断

workflow 不进入执行态

记录 agent_run 错误

可 fallback 或人工接管

F2：recommendation 缺少 evidence_ids

预期

recommendation 不可进入审批通过后的执行

页面展示“证据缺失”

审计日志记录拦截原因

F3：审批任务丢失 / 重复

预期

系统不能生成重复执行动作

幂等逻辑生效

任务状态可追踪

F4：外部执行连接器失败

预期

workflow 进入 FAILED_RETRYABLE 或 WAITING_MANUAL

retry 可恢复

不出现重复提交

F5：服务重启

预期

重启后 run 可恢复

checkpoint 不丢失

UI 可查看恢复前后状态

F6：回调重复到达

预期

幂等处理

不重复推进状态

审计日志只记录一次有效推进

F7：审批驳回

预期

workflow 转 REJECTED 或 REWORK

原始建议保留

允许重开版本

F8：模型超时

预期

节点超时被记录

fallback 到规则建议或人工处理

页面不崩溃

10. 自测维度
10.1 功能正确性

验证结果是否符合产品逻辑。

关注点：

风险等级是否正确

推荐动作是否符合规则

审批结果是否正确反映到状态

导出内容是否完整

10.2 流程完整性

验证状态是否正确推进。

关注点：

workflow 节点顺序

pause / resume 是否生效

审批后是否继续

失败后是否可 retry

10.3 数据一致性

验证页面、接口、数据库、导出之间是否一致。

关注点：

指标计算一致

evidence_id 对应正确

final_action_json 与页面最终结果一致

10.4 可审计性

验证是否可追溯。

关注点：

audit log 完整

trace 可查看

agent_run 可追踪

审批记录完整

10.5 安全与守卫

验证系统是否能拦截危险输出和危险动作。

关注点：

无审批不可执行

schema 不合法不可通过

敏感动作需审批

禁止语义输出被阻断

10.6 稳定性与恢复

验证系统在异常场景下是否能稳定运行。

关注点：

服务重启

callback 延迟

工具失败

模型失败

checkpoint 恢复

10.7 性能与可用性

验证是否满足上线底线。

关注点：

核心接口响应时间

案件分析耗时

trace 加载耗时

审批操作成功率

11. 测试数据要求
11.1 数据集要求

需要准备系统级自测专用 seed 数据集，至少包含：

50 个商家

90 天订单数据

退货、退款、物流、结算数据完整

4 类典型风险场景

2 类边界场景

2 类异常数据场景

11.2 必备样本类型
正常样本

指标平稳

不触发案件

高退货样本

退货率明显提升

但资金情况不同

回款延迟样本

资金回流异常

存在待结算

异常退货样本

多信号命中

边界样本

刚好达到阈值

刚好不达到阈值

脏数据样本

settlement 缺失

logistics 时间乱序

order 与 return 不一致

12. 自测环境要求
12.1 环境分层

系统级自测必须在独立环境进行，建议：

dev：开发自测

sit：系统联调

uat：业务验收 / 预发自测

12.2 环境要求

独立数据库

独立对象存储 / 文件导出路径

可切换 mock connector / sandbox connector

trace、日志、监控齐全

支持人工审批账号与角色权限配置

12.3 自测前置条件

最新 schema 已迁移

seed 数据已初始化

模型 / prompt / schema version 已固定

连接器沙箱可用

审批角色账号已创建

13. 自测执行流程
13.1 执行阶段
阶段 A：冒烟

确认系统可用、关键页面可打开、核心接口可调通。

阶段 B：核心链路

执行 5 个 P0 业务场景。

阶段 C：异常链路

执行失败、审批驳回、服务重启、重复回调等场景。

阶段 D：门禁验证

检查覆盖率、缺陷、指标、日志、trace、性能。

13.2 执行角色

产品：确认业务预期

研发：执行技术路径自测

测试：组织系统验证

算法 / Agent 工程师：确认输出质量

业务方：参与 UAT 样本验收

13.3 输出物

每次系统级自测必须输出：

自测报告

场景执行记录

失败案例清单

缺陷单列表

run_id / case_id / trace_id 对照表

上线门禁结论

14. 指标与上线门禁
14.1 P0 上线门禁

以下必须全部满足：

功能门禁

所有 P0 核心场景通过

所有敏感动作审批门生效

所有 recommendation 有 evidence_ids

所有导出结果可生成

质量门禁

schema 合格率 >= 99%

recommendation 证据覆盖率 >= 95%

审批日志完整率 = 100%

trace 完整率 >= 95%

稳定性门禁

服务重启恢复成功率 >= 95%

retryable 失败恢复率 >= 90%

外部写动作无重复执行

缺陷门禁

P0 缺陷 = 0

P1 缺陷已评审并可接受

无阻断上线的安全问题

性能门禁

核心查询接口 P95 < 1s

单案件重分析 P95 < 20s

审批操作成功率 > 99%

15. 缺陷分级标准
P0

高风险动作绕过审批

工作流状态错乱导致重复执行

服务重启后 checkpoint 丢失

recommendation 无证据仍可执行

导出与实际审批结论不一致

P1

关键页面核心信息缺失

trace 无法查看

审批通过后 workflow 不恢复

外部执行失败未正确进入 retry/manual

P2

次要字段显示错误

非核心日志缺失

非关键图表展示异常

16. 自测报告模板要求

系统级自测完成后，必须输出统一报告，包含：

16.1 基本信息

测试版本

环境

执行时间

负责人

覆盖模块

16.2 执行摘要

总场景数

通过数

失败数

阻塞数

风险结论

16.3 核心场景结果

逐条列出：

场景编号

输入数据

执行路径

run_id

结果

缺陷链接

16.4 指标结果

schema 合格率

evidence 覆盖率

trace 完整率

审批完整率

性能结果

16.5 上线建议

可上线

限制上线

不可上线

17. 非功能专项自测要求
17.1 审计专项

验证：

所有状态变化有审计记录

审批意见可追溯

actor / time / action 完整

17.2 恢复专项

验证：

pause / resume

retry

restart recovery

callback replay

17.3 守卫专项

验证：

禁止输出拦截

敏感动作审批

参数异常拦截

schema 校验失败拦截

17.4 导出专项

验证：

markdown / json 导出成功

数值一致

recommendation 与 evidence 匹配

审批结果同步

18. 后续演进建议

当前系统级自测 PRD 先覆盖上线前必需项。后续建议迭代到以下能力：

回归自测集

固定一批 case 回放

每次 prompt / model 升级自动回归

线上抽样复盘

抽样检查 recommendation 质量

统计人工改写率和驳回率

自动门禁

CI/CD 接入 schema、trace、核心接口门禁

评测中心联动

将系统级自测结果沉淀为 eval dataset

19. 一句话版本结论

这份系统级自测 PRD 的核心，不是“测几个页面”，而是确保你的系统在第三阶段已经具备：

能跑通、能阻断、能恢复、能审批、能追责、能上线。