## ADDED Requirements

### Requirement: 14 日现金流预测
系统 SHALL 提供函数 forecast_cash_gap(merchant_id, horizon_days=14)，输出未来 14 天每日的 inflow（收入）、outflow（支出）、netflow（净流）。

#### Scenario: 正常预测输出
- **WHEN** 调用 forecast_cash_gap(merchant_id="M-001", horizon_days=14)
- **THEN** 返回包含 14 天每日 inflow/outflow/netflow 的数组，以及 predicted_gap、lowest_cash_day、confidence 字段

#### Scenario: 缺口预测
- **WHEN** 商家近期退款增加、回款延迟
- **THEN** predicted_gap 为正数（表示缺口金额），lowest_cash_day 为缺口最大的日期

### Requirement: 预测方法使用滚动均值加季节性系数
预测 SHALL 使用滚动均值 + 简单季节性系数（周几系数）+ 已知应收/应付计划，MUST NOT 使用机器学习模型训练。

#### Scenario: 季节性调整
- **WHEN** 商家周末订单量通常低于工作日
- **THEN** 预测的周末 inflow 低于工作日 inflow

#### Scenario: 已知应收纳入预测
- **WHEN** 商家有一笔预计 T+5 到账的回款 50,000 元
- **THEN** 该笔回款体现在 T+5 的 inflow 中

### Requirement: 预测置信度输出
预测结果 SHALL 包含 confidence 字段（0-1），基于历史数据波动性计算。数据波动越大，置信度越低。

#### Scenario: 高置信度
- **WHEN** 商家近 30 日经营数据波动小（标准差低）
- **THEN** confidence >= 0.7

#### Scenario: 低置信度
- **WHEN** 商家近 30 日经营数据波动大
- **THEN** confidence < 0.5

### Requirement: 预测函数可单元测试
forecast_cash_gap 函数 SHALL 接受确定性输入并产生确定性输出，支持独立单元测试。

#### Scenario: 确定性输出
- **WHEN** 给定一组固定的历史数据和应收/应付计划
- **THEN** 预测结果完全一致，可通过断言验证
