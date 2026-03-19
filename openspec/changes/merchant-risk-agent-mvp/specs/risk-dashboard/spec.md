## ADDED Requirements

### Requirement: 顶部指标卡展示
风险看板页面 SHALL 在顶部显示以下 4 个指标卡：
- 监控商家数
- 今日新增高风险案件数
- 预计总现金缺口
- 平均回款延迟天数

#### Scenario: 指标卡数据加载
- **WHEN** 用户打开风险看板页面
- **THEN** 顶部显示 4 个指标卡，数据从后端 API 实时获取

### Requirement: 筛选区
页面 SHALL 提供以下筛选条件：风险等级、行业、回款周期、是否有融资资格、日期范围。

#### Scenario: 按风险等级筛选
- **WHEN** 用户选择风险等级为 "high"
- **THEN** 列表仅显示 risk_level 为 high 的案件

#### Scenario: 多条件筛选
- **WHEN** 用户同时选择风险等级 "high" 和行业 "女装"
- **THEN** 列表仅显示同时满足两个条件的案件

### Requirement: 案件列表展示
页面 SHALL 展示案件列表，每行包含：商家名称、行业、7 日退货率、基线退货率、退货率放大倍数、14 日预测缺口、风险等级、建议动作数、案件状态、更新时间。

#### Scenario: 列表数据展示
- **WHEN** 数据库中有风险案件
- **THEN** 列表正确展示每条案件的所有字段

#### Scenario: 空状态
- **WHEN** 没有风险案件
- **THEN** 显示"暂无风险案件"的空状态提示

### Requirement: 列表排序
页面 SHALL 支持按"预测缺口"、"风险等级"、"更新时间"排序。

#### Scenario: 按预测缺口降序排序
- **WHEN** 用户点击"预测缺口"列头
- **THEN** 列表按 14 日预测缺口从大到小排序

### Requirement: 点击进入详情
点击列表中的案件行 SHALL 导航到案件详情页。

#### Scenario: 导航到详情
- **WHEN** 用户点击案件 RC-0001 所在行
- **THEN** 页面跳转到 /cases/RC-0001 详情页

### Requirement: 重新分析按钮
页面 SHALL 提供"重新分析"按钮，触发后端重新运行 Agent 分析。

#### Scenario: 重新分析
- **WHEN** 用户点击某案件的"重新分析"按钮
- **THEN** 调用 POST /api/risk-cases/{case_id}/analyze，页面显示加载状态，完成后刷新数据

### Requirement: 页面响应式设计
页面 SHALL 使用 Tailwind CSS 实现响应式布局，在 1280px 及以上宽度下正常展示所有列。

#### Scenario: 首屏加载
- **WHEN** 用户访问风险看板页面
- **THEN** 页面首屏加载成功，指标卡和列表正常显示
