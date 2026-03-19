## ADDED Requirements

### Requirement: 融资资格判断规则
系统 SHALL 提供融资资格判断函数，根据商家经营数据和融资产品规则判断商家是否符合融资申请条件。

#### Scenario: 商家符合融资资格
- **WHEN** 商家满足以下全部条件：(1) 近 90 天总销售额 > 融资产品最低销售额要求；(2) 退货率 < 融资产品最大允许退货率；(3) 回款延迟天数 < 融资产品最大允许延迟天数；(4) 店铺等级在融资产品允许等级列表中
- **THEN** 函数返回 eligible=True，同时返回推荐融资金额（取预测现金缺口与融资产品最大额度的较小值）

#### Scenario: 商家不符合融资资格
- **WHEN** 商家不满足融资资格的任一条件
- **THEN** 函数返回 eligible=False，同时返回 rejection_reasons 列表（如"退货率超过阈值"）

#### Scenario: 无可用融资产品
- **WHEN** 数据库中没有 status=active 的融资产品
- **THEN** 函数返回 eligible=False，rejection_reasons=["无可用融资产品"]

### Requirement: 理赔条件匹配规则
系统 SHALL 提供理赔条件匹配函数，根据商家的保险保单和退货数据判断是否可以发起理赔。

#### Scenario: 商家有有效保单且退货符合理赔条件
- **WHEN** 商家存在 status=active 的保险保单，且退货金额未超过保单覆盖上限
- **THEN** 函数返回 eligible=True，同时返回匹配的 policy_id 和可理赔金额

#### Scenario: 退货金额超过保单覆盖上限
- **WHEN** 商家的退货总金额超过保单的 coverage_limit
- **THEN** 函数返回 eligible=True，但可理赔金额 MUST 限制在 coverage_limit 以内

#### Scenario: 商家无有效保单
- **WHEN** 商家不存在任何 status=active 的保险保单
- **THEN** 函数返回 eligible=False，rejection_reasons=["无有效保险保单"]

### Requirement: 复核触发条件评估规则
系统 SHALL 提供复核触发条件评估函数，根据商家的异常行为判断是否需要生成人工复核任务。

#### Scenario: 退货率异常放大触发复核
- **WHEN** 商家 7 日退货率相对基线的放大倍数 >= 2.0（return_amplification >= 2.0）
- **THEN** 函数返回 should_review=True，review_type="return_fraud"，review_reason 描述退货率异常情况

#### Scenario: 高风险强制复核
- **WHEN** 案件 risk_level 为 "high" 且 Agent 输出中 manual_review_required 为 true
- **THEN** 函数返回 should_review=True，review_type="high_risk_mandatory"

#### Scenario: 正常退货率不触发复核
- **WHEN** 商家退货率放大倍数 < 1.5 且 risk_level 不为 "high"
- **THEN** 函数返回 should_review=False

### Requirement: 任务生成引擎整合
系统 SHALL 提供统一的任务生成引擎（`services/task_generator.py`），在 Agent 分析完成或审批通过后，遍历所有建议并调用规则引擎判断，自动生成对应的执行任务。

#### Scenario: 分析完成后自动生成任务
- **WHEN** Agent 分析流程完成（案件状态变为 ANALYZED），Orchestrator 调用任务生成引擎
- **THEN** 引擎遍历所有 Recommendation，对每个建议调用对应的规则判断，符合条件的自动生成任务，并标记 Recommendation.task_generated=True

#### Scenario: 审批通过后自动生成任务
- **WHEN** 案件审批通过（状态变为 APPROVED），审批服务调用任务生成引擎
- **THEN** 引擎对尚未生成任务的 Recommendation 进行评估和生成

#### Scenario: 幂等性保证
- **WHEN** 对同一个 Recommendation 重复调用任务生成
- **THEN** 如果 task_generated 已为 True，引擎跳过该建议，不重复生成任务
