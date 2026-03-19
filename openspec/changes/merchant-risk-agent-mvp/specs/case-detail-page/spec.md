## ADDED Requirements

### Requirement: 左侧商家基本信息
案件详情页左侧 SHALL 展示商家名称、行业、店铺等级、结算周期等基本信息。

#### Scenario: 商家信息展示
- **WHEN** 用户打开案件详情页
- **THEN** 左侧显示关联商家的完整基本信息

### Requirement: 最近 30 天趋势图
左侧 SHALL 展示最近 30 天的趋势图，包含订单金额、退货率、退款金额、回款金额四条曲线。

#### Scenario: 趋势图渲染
- **WHEN** 案件详情页加载完成
- **THEN** 使用 Recharts 渲染 30 天趋势折线图，支持悬浮查看具体数值

### Requirement: 风险评分拆解
左侧 SHALL 展示风险评分的拆解，包含各维度得分（退货率放大、回款延迟、退款压力、异常退货分数）。

#### Scenario: 评分拆解展示
- **WHEN** 案件详情页加载完成
- **THEN** 显示每个维度的得分和权重

### Requirement: 14 日现金流预测图
左侧 SHALL 展示未来 14 天的现金流预测图，包含每日 inflow/outflow/netflow 和累计缺口线。

#### Scenario: 预测图渲染
- **WHEN** 案件详情页加载完成
- **THEN** 预测图显示 14 天数据，最低现金点用醒目标记

### Requirement: 右侧 Agent 案件总结
右侧 SHALL 展示 Agent 生成的案件摘要，包含风险等级标签、摘要文本、核心成因列表。

#### Scenario: 摘要展示
- **WHEN** 案件状态为 ANALYZED 或之后
- **THEN** 右侧显示 Agent 摘要和根因列表

#### Scenario: 未分析状态
- **WHEN** 案件状态为 NEW
- **THEN** 右侧显示"待分析"提示和"开始分析"按钮

### Requirement: 右侧动作建议列表
右侧 SHALL 展示 Agent 推荐的动作建议列表，每条包含标题、原因、预期收益、置信度、是否需要人工复核标签。

#### Scenario: 建议列表展示
- **WHEN** 案件有 3 条动作建议
- **THEN** 列表展示 3 条建议卡片，人工复核标签醒目显示

### Requirement: 右侧证据引用
每条根因和建议 SHALL 可点击展开关联的证据详情。

#### Scenario: 证据展开
- **WHEN** 用户点击根因旁的 evidence_id 链接
- **THEN** 展开显示该证据的原始数据摘要

### Requirement: 底部证据链时间线
底部 SHALL 展示证据链时间线，按时间顺序展示所有证据事件。

#### Scenario: 时间线展示
- **WHEN** 案件有 10 条证据记录
- **THEN** 底部时间线按时间排序展示所有证据节点

### Requirement: 底部原始记录表格
底部 SHALL 展示原始记录表格（订单、退货、回款等原始数据），支持分页。

#### Scenario: 原始数据查看
- **WHEN** 用户切换到"原始记录"标签页
- **THEN** 显示关联的订单、退货等原始数据表格

### Requirement: 底部审计记录
底部 SHALL 展示案件的审计记录列表，按时间倒序排列。

#### Scenario: 审计记录展示
- **WHEN** 案件经历了创建、分析、审批操作
- **THEN** 审计记录显示每次操作的时间、操作人、操作类型和变更内容
