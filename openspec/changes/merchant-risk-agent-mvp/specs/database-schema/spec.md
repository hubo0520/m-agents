## ADDED Requirements

### Requirement: 12 张核心业务表定义
系统 SHALL 包含以下 12 张数据库表：merchants、orders、returns、logistics_events、settlements、insurance_policies、financing_products、risk_cases、evidence_items、recommendations、reviews、audit_logs。每张表 SHALL 包含 id 主键和必要的外键关系。

#### Scenario: 数据库初始化成功
- **WHEN** 运行数据库迁移脚本
- **THEN** 所有 12 张表成功创建，表结构与数据模型定义一致

#### Scenario: 外键关系正确
- **WHEN** 查询 risk_cases 表的 merchant_id 字段
- **THEN** 该字段正确关联到 merchants 表的 id

#### Scenario: 索引创建
- **WHEN** 数据库初始化完成
- **THEN** risk_cases 表的 merchant_id、status、risk_level 字段有索引

### Requirement: merchants 表结构
merchants 表 SHALL 包含 id、name、industry、settlement_cycle_days、store_level、created_at 字段。

#### Scenario: 商家记录存储
- **WHEN** 插入一条商家记录，包含 name="测试商家"、industry="女装"、settlement_cycle_days=7、store_level="gold"
- **THEN** 记录成功插入，自动生成 id 和 created_at

### Requirement: risk_cases 表结构
risk_cases 表 SHALL 包含 id、merchant_id、risk_score、risk_level、trigger_json、status、agent_output_json、created_at、updated_at 字段。status 字段 SHALL 支持 NEW/ANALYZED/PENDING_REVIEW/APPROVED/REJECTED 枚举。

#### Scenario: 案件创建
- **WHEN** 风险引擎创建一条新案件
- **THEN** 案件状态默认为 NEW，trigger_json 记录触发条件

### Requirement: evidence_items 表结构
evidence_items 表 SHALL 包含 id、case_id、evidence_type、source_table、source_id、summary、importance_score 字段。

#### Scenario: 证据关联案件
- **WHEN** 为案件 RC-0001 创建一条证据记录
- **THEN** evidence_items 的 case_id 正确关联到 risk_cases 表

### Requirement: audit_logs 表结构
audit_logs 表 SHALL 包含 id、entity_type、entity_id、actor、action、old_value、new_value、created_at 字段。

#### Scenario: 审计日志记录
- **WHEN** 对案件进行审批操作
- **THEN** audit_logs 表生成一条记录，包含操作前后的状态值
