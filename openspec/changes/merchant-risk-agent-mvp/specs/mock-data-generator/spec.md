## ADDED Requirements

### Requirement: 生成 50 个商家基础数据
系统 SHALL 生成 50 个商家记录，覆盖女装、数码、家居、食品、美妆等行业，settlement_cycle_days 在 3-14 天之间随机分配，store_level 包含 gold/silver/bronze 三级。

#### Scenario: 商家数量正确
- **WHEN** 运行 mock 数据生成器
- **THEN** merchants 表中生成 50 条商家记录

#### Scenario: 行业分布合理
- **WHEN** 查询所有商家的行业分布
- **THEN** 至少覆盖 5 个不同行业

### Requirement: 生成 90 天经营数据
系统 SHALL 为每个商家生成近 90 天的订单、退货、物流事件、回款记录，数据时间范围覆盖 T-90 到 T-1。

#### Scenario: 订单数据量合理
- **WHEN** 运行 mock 数据生成器
- **THEN** 每个商家平均每日有 5-50 笔订单，总订单量在 22500-225000 之间

#### Scenario: 退货数据关联订单
- **WHEN** 查询 returns 表中的记录
- **THEN** 每条退货记录的 order_id 在 orders 表中存在

### Requirement: 覆盖 3 类风险场景
数据生成器 SHALL 确保 50 个商家中包含以下 3 类风险场景：
- 场景 A（约 8-12 个商家）：高退货 + 回款延迟 — 近 7 日退货率 >= 20%，回款延迟 >= 3 天
- 场景 B（约 5-8 个商家）：高退货但现金充足 — 近 7 日退货率 >= 18%，但回款正常
- 场景 C（约 3-5 个商家）：疑似异常退货 — 同一地址/账号短期高频退货模式

#### Scenario: 场景 A 商家存在
- **WHEN** 分析生成的数据
- **THEN** 至少有 8 个商家的 7 日退货率 >= 20% 且平均回款延迟 >= 3 天

#### Scenario: 场景 C 异常模式
- **WHEN** 分析场景 C 商家的退货数据
- **THEN** 存在同一退货原因在短期内高频出现的模式

### Requirement: 数据可重复生成
数据生成器 SHALL 支持设置随机种子（seed），确保同一种子下生成的数据完全一致。

#### Scenario: 种子一致性
- **WHEN** 使用相同的 seed=42 运行两次数据生成器
- **THEN** 两次生成的数据完全相同
