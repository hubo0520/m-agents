## ADDED Requirements

### Requirement: 基于规则自动生成风险案件
系统 SHALL 按日扫描商家经营数据，满足以下任一条件时自动生成风险案件：
- 7 日退货率 / 28 日基线退货率 >= 1.6
- 14 日预测现金缺口 >= 50,000
- 平均回款延迟天数 >= 3
- 疑似异常退货信号分数 >= 阈值（默认 0.8）

#### Scenario: 高退货率触发案件
- **WHEN** 某商家 7 日退货率 24%，28 日基线退货率 12%，放大倍数 2.0
- **THEN** 系统生成一条风险案件，trigger_json 中记录 "return_rate_amplification >= 1.6"

#### Scenario: 现金缺口触发案件
- **WHEN** 某商家 14 日预测现金缺口为 86,000 元
- **THEN** 系统生成一条风险案件，trigger_json 中记录 "predicted_gap >= 50000"

#### Scenario: 多条件同时触发
- **WHEN** 某商家同时满足退货率放大和回款延迟条件
- **THEN** 只生成一条案件，trigger_json 中记录所有触发条件

### Requirement: 风险等级自动评定
系统 SHALL 根据以下规则评定风险等级：
- High：退货率放大倍数 >= 1.6 且 14 日缺口 >= 50,000，或疑似异常退货分数 >= 0.8
- Medium：退货率放大倍数 >= 1.3，或平均回款延迟 >= 2 天
- Low：其余

#### Scenario: High 风险等级
- **WHEN** 商家退货率放大倍数 2.0 且 14 日缺口 86,000
- **THEN** 案件 risk_level 为 "high"

#### Scenario: Medium 风险等级
- **WHEN** 商家退货率放大倍数 1.4，无现金缺口
- **THEN** 案件 risk_level 为 "medium"

### Requirement: 避免重复生成案件
系统 SHALL 对同一商家在同一天不重复生成案件。若已有未关闭的案件，SHALL 更新而非新建。

#### Scenario: 不重复生成
- **WHEN** 商家 M-001 已有一条状态为 NEW 的案件，再次运行扫描
- **THEN** 不生成新案件，更新已有案件的指标数据

### Requirement: 案件生成批量执行
系统 SHALL 支持一次性扫描所有商家并批量生成案件，单次执行后可生成至少 5 条有效案件。

#### Scenario: 批量生成
- **WHEN** 运行风险案件生成脚本
- **THEN** 至少生成 5 条有效案件，每条案件关联到商家和原始记录
