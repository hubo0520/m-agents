## ADDED Requirements

### Requirement: 7 日退货率计算
系统 SHALL 提供函数 compute_return_rate(merchant_id, days=7)，计算指定商家近 N 天的退货率（退货订单数 / 总订单数）。

#### Scenario: 正常计算
- **WHEN** 商家近 7 日有 100 笔订单，24 笔退货
- **THEN** 返回退货率 0.24（24%）

#### Scenario: 无订单时
- **WHEN** 商家近 7 日无订单
- **THEN** 返回退货率 0.0

### Requirement: 28 日基线退货率计算
系统 SHALL 提供函数 compute_baseline_return_rate(merchant_id)，计算近 28 日的退货率作为基线。

#### Scenario: 基线计算
- **WHEN** 商家近 28 日有 500 笔订单，60 笔退货
- **THEN** 返回基线退货率 0.12（12%）

### Requirement: 退货率放大倍数计算
系统 SHALL 提供函数 compute_return_amplification(merchant_id)，返回 7 日退货率 / 28 日基线退货率。

#### Scenario: 放大倍数
- **WHEN** 7 日退货率 0.24，28 日基线 0.12
- **THEN** 返回放大倍数 2.0

#### Scenario: 基线为零
- **WHEN** 28 日基线退货率为 0
- **THEN** 返回放大倍数 0.0（安全处理除零）

### Requirement: 平均回款延迟计算
系统 SHALL 提供函数 compute_avg_settlement_delay(merchant_id)，计算近 30 天内已回款记录的平均延迟天数（actual_settlement_date - expected_settlement_date）。

#### Scenario: 延迟计算
- **WHEN** 商家有 10 笔回款，平均延迟 3.2 天
- **THEN** 返回 3.2

### Requirement: 退款压力计算
系统 SHALL 提供函数 compute_refund_pressure(merchant_id, days)，返回指定天数内的退款总金额。

#### Scenario: 7 日退款压力
- **WHEN** 商家近 7 日退款总额 15,000 元
- **THEN** 返回 15000.0

### Requirement: 异常退货分数计算
系统 SHALL 提供函数 compute_anomaly_score(merchant_id)，基于以下信号计算 0-1 之间的异常分数：
- 同一退货原因短期高频出现
- 签收后极短时间内退款
- 退货率突变幅度

#### Scenario: 高异常分数
- **WHEN** 商家存在多笔签收后 24 小时内退款且退货原因相同
- **THEN** 异常分数 >= 0.8

#### Scenario: 正常商家
- **WHEN** 商家退货模式正常
- **THEN** 异常分数 < 0.3

### Requirement: 所有数值由 Python 函数计算
所有指标计算 MUST 由 Python 函数完成，MUST NOT 由 LLM 生成或编造数字。每个函数 SHALL 可独立单元测试。

#### Scenario: 函数可测试
- **WHEN** 给定一组确定的测试数据
- **THEN** 每个指标函数输出确定性结果，可通过断言验证
