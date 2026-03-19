"""
Mock 数据生成器 — 生成 50 个商家 × 90 天经营数据 × 3 类风险场景

使用方法：
    python scripts/generate_mock_data.py [--seed 42]
"""
import sys
import os
import random
import json
import argparse
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, Base, SessionLocal
from app.models.models import (
    Merchant, Order, Return, LogisticsEvent, Settlement,
    InsurancePolicy, FinancingProduct,
    RiskCase, WorkflowRun, AgentRun, ApprovalTask,
    PromptVersion, SchemaVersion, EvalDataset, ToolInvocation,
)

# ────────────────────── 常量 ──────────────────────

INDUSTRIES = ["女装", "数码", "家居", "食品", "美妆", "运动", "母婴", "宠物"]
STORE_LEVELS = ["gold", "silver", "bronze"]
RETURN_REASONS = [
    "尺码不合适", "质量问题", "与描述不符", "不喜欢/不想要",
    "发错商品", "物流损坏", "假冒伪劣", "其他",
]
SKU_PREFIXES = ["SKU-A", "SKU-B", "SKU-C", "SKU-D", "SKU-E"]
LOGISTICS_EVENTS = ["picked_up", "in_transit", "delivered", "returned"]

# 场景分配：A=高退货+回款延迟, B=高退货但现金充足, C=异常退货模式, N=正常
SCENARIO_A_COUNT = 10  # 8-12
SCENARIO_B_COUNT = 6   # 5-8
SCENARIO_C_COUNT = 4   # 3-5
TOTAL_MERCHANTS = 50
DAYS = 90

TODAY = date.today()
START_DATE = TODAY - timedelta(days=DAYS)


def generate_merchants(session, rng: random.Random) -> list:
    """生成 50 个商家"""
    merchants = []
    for i in range(TOTAL_MERCHANTS):
        m = Merchant(
            name=f"测试商家{i+1:03d}",
            industry=rng.choice(INDUSTRIES),
            settlement_cycle_days=rng.randint(3, 14),
            store_level=rng.choice(STORE_LEVELS),
            created_at=datetime.combine(
                START_DATE - timedelta(days=rng.randint(30, 365)), datetime.min.time()
            ),
        )
        session.add(m)
        merchants.append(m)
    session.flush()
    print(f"  ✓ 生成 {len(merchants)} 个商家")
    return merchants


def _assign_scenarios(rng: random.Random) -> dict:
    """为 50 个商家分配风险场景"""
    indices = list(range(TOTAL_MERCHANTS))
    rng.shuffle(indices)

    scenario_map = {}
    pos = 0
    for idx in indices[pos:pos + SCENARIO_A_COUNT]:
        scenario_map[idx] = "A"
    pos += SCENARIO_A_COUNT
    for idx in indices[pos:pos + SCENARIO_B_COUNT]:
        scenario_map[idx] = "B"
    pos += SCENARIO_B_COUNT
    for idx in indices[pos:pos + SCENARIO_C_COUNT]:
        scenario_map[idx] = "C"
    pos += SCENARIO_C_COUNT
    for idx in indices[pos:]:
        scenario_map[idx] = "N"

    return scenario_map


def generate_orders_and_returns(session, merchants, scenario_map, rng: random.Random):
    """生成 90 天订单和退货数据"""
    total_orders = 0
    total_returns = 0

    for mi, merchant in enumerate(merchants):
        scenario = scenario_map[mi]
        daily_orders_base = rng.randint(8, 40)

        for day_offset in range(DAYS):
            current_date = START_DATE + timedelta(days=day_offset)
            is_recent_7 = day_offset >= (DAYS - 7)

            # 每日订单数带随机波动
            daily_count = max(5, int(daily_orders_base * rng.uniform(0.6, 1.4)))
            orders_today = []

            for _ in range(daily_count):
                order_time = datetime.combine(current_date, datetime.min.time()) + timedelta(
                    hours=rng.randint(8, 22), minutes=rng.randint(0, 59)
                )
                amount = round(rng.uniform(20, 800), 2)
                sku_id = f"{rng.choice(SKU_PREFIXES)}-{rng.randint(1, 20):03d}"

                delivered_time = order_time + timedelta(
                    days=rng.randint(1, 5), hours=rng.randint(0, 12)
                ) if rng.random() > 0.05 else None

                order = Order(
                    merchant_id=merchant.id,
                    sku_id=sku_id,
                    order_amount=amount,
                    order_time=order_time,
                    delivered_time=delivered_time,
                )
                session.add(order)
                orders_today.append(order)
                total_orders += 1

            session.flush()

            # 根据场景确定退货率
            if scenario == "A":
                # 近 7 日退货率高（>=20%），其余时间正常（~12%）
                return_rate = rng.uniform(0.22, 0.35) if is_recent_7 else rng.uniform(0.08, 0.15)
            elif scenario == "B":
                # 近 7 日退货率高（>=18%），但回款正常
                return_rate = rng.uniform(0.20, 0.30) if is_recent_7 else rng.uniform(0.08, 0.14)
            elif scenario == "C":
                # 退货率中等，但有异常模式
                return_rate = rng.uniform(0.12, 0.20)
            else:
                # 正常商家
                return_rate = rng.uniform(0.03, 0.10)

            # 生成退货
            num_returns = int(len(orders_today) * return_rate)
            returned_orders = rng.sample(orders_today, min(num_returns, len(orders_today)))

            for order in returned_orders:
                if order.delivered_time is None:
                    continue

                # 场景 C：异常退货 — 集中使用相同原因、签收后极短时间退
                if scenario == "C" and rng.random() > 0.4:
                    reason = "不喜欢/不想要"  # 集中同一原因
                    hours_after_delivery = rng.uniform(0.5, 6)  # 签收后极短时间
                else:
                    reason = rng.choice(RETURN_REASONS)
                    hours_after_delivery = rng.uniform(12, 168)

                return_time = order.delivered_time + timedelta(hours=hours_after_delivery)
                refund_amount = round(order.order_amount * rng.uniform(0.8, 1.0), 2)

                ret = Return(
                    order_id=order.id,
                    return_reason=reason,
                    return_time=return_time,
                    refund_amount=refund_amount,
                    status="completed",
                )
                session.add(ret)
                total_returns += 1

    session.flush()
    print(f"  ✓ 生成 {total_orders} 笔订单, {total_returns} 笔退货")


def generate_logistics(session, rng: random.Random):
    """为所有订单生成物流事件"""
    orders = session.query(Order).all()
    count = 0
    for order in orders:
        # 揽收事件
        pickup_time = order.order_time + timedelta(hours=rng.randint(1, 8))
        session.add(LogisticsEvent(
            order_id=order.id, event_type="picked_up", event_time=pickup_time
        ))

        # 运输中
        transit_time = pickup_time + timedelta(hours=rng.randint(4, 24))
        session.add(LogisticsEvent(
            order_id=order.id, event_type="in_transit", event_time=transit_time
        ))

        if order.delivered_time:
            session.add(LogisticsEvent(
                order_id=order.id, event_type="delivered", event_time=order.delivered_time
            ))

        # 如果有退货，加退回事件
        if order.returns:
            for ret in order.returns:
                session.add(LogisticsEvent(
                    order_id=order.id, event_type="returned",
                    event_time=ret.return_time + timedelta(hours=rng.randint(2, 24))
                ))
        count += 1

    session.flush()
    print(f"  ✓ 生成 {count} 条订单的物流事件")


def generate_settlements(session, merchants, scenario_map, rng: random.Random):
    """生成回款数据"""
    count = 0
    for mi, merchant in enumerate(merchants):
        scenario = scenario_map[mi]
        cycle = merchant.settlement_cycle_days

        # 每隔结算周期生成一笔回款
        current = START_DATE
        while current < TODAY:
            expected_date = current + timedelta(days=cycle)
            amount = round(rng.uniform(5000, 80000), 2)

            if scenario == "A":
                # 回款延迟 3-8 天
                delay_days = rng.randint(3, 8)
                actual_date = expected_date + timedelta(days=delay_days)
                status = "delayed" if actual_date > TODAY else "settled"
                if actual_date > TODAY:
                    actual_date = None
                    status = "delayed"
            elif scenario == "B":
                # 回款正常或轻微延迟
                delay_days = rng.randint(0, 1)
                actual_date = expected_date + timedelta(days=delay_days)
                status = "settled"
            else:
                # 正常回款
                delay_days = rng.choice([0, 0, 0, 1])
                actual_date = expected_date + timedelta(days=delay_days)
                status = "settled"

            if actual_date and actual_date > TODAY:
                actual_date = None
                status = "pending"

            s = Settlement(
                merchant_id=merchant.id,
                expected_settlement_date=expected_date,
                actual_settlement_date=actual_date,
                amount=amount,
                status=status,
            )
            session.add(s)
            count += 1
            current = expected_date

    session.flush()
    print(f"  ✓ 生成 {count} 笔回款记录")


def generate_insurance_and_financing(session, merchants, rng: random.Random):
    """生成保险保单和融资产品"""
    # 保险保单
    insurance_count = 0
    for merchant in merchants:
        if rng.random() > 0.3:  # 70% 的商家有运费险
            policy = InsurancePolicy(
                merchant_id=merchant.id,
                policy_type="shipping_return",
                coverage_limit=round(rng.uniform(50000, 500000), 2),
                premium_rate=round(rng.uniform(0.005, 0.02), 4),
                status="active",
            )
            session.add(policy)
            insurance_count += 1

    # 融资产品
    products = [
        FinancingProduct(
            name="快速回款加速",
            max_amount=500000,
            eligibility_rule_json=json.dumps({
                "min_operation_days": 30,
                "min_store_level": "bronze",
                "min_total_sales_90d": 50000,
                "max_return_rate": 0.30,
                "max_settlement_delay": 10,
            }),
            status="active",
        ),
        FinancingProduct(
            name="商家经营贷",
            max_amount=1000000,
            eligibility_rule_json=json.dumps({
                "min_operation_days": 60,
                "min_store_level": "silver",
                "max_dispute_rate": 0.05,
                "min_total_sales_90d": 100000,
                "max_return_rate": 0.25,
                "max_settlement_delay": 8,
            }),
            status="active",
        ),
        FinancingProduct(
            name="运费险升级方案",
            max_amount=200000,
            eligibility_rule_json=json.dumps({
                "min_operation_days": 15,
                "min_total_sales_90d": 20000,
                "max_return_rate": 0.35,
                "max_settlement_delay": 15,
            }),
            status="active",
        ),
    ]
    for p in products:
        session.add(p)

    session.flush()
    print(f"  ✓ 生成 {insurance_count} 个保险保单, {len(products)} 个融资产品")


def main():
    parser = argparse.ArgumentParser(description="Mock 数据生成器")
    parser.add_argument("--seed", type=int, default=42, help="随机种子（默认 42）")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    print(f"使用随机种子: {args.seed}")

    # 重建数据库
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        print("\n[1/5] 生成商家...")
        merchants = generate_merchants(session, rng)

        print("\n[2/5] 分配风险场景...")
        scenario_map = _assign_scenarios(rng)
        scenario_counts = {}
        for s in scenario_map.values():
            scenario_counts[s] = scenario_counts.get(s, 0) + 1
        print(f"  场景分配: A(高退货+回款延迟)={scenario_counts.get('A', 0)}, "
              f"B(高退货但现金充足)={scenario_counts.get('B', 0)}, "
              f"C(异常退货)={scenario_counts.get('C', 0)}, "
              f"N(正常)={scenario_counts.get('N', 0)}")

        print("\n[3/5] 生成订单和退货数据...")
        generate_orders_and_returns(session, merchants, scenario_map, rng)

        print("\n[4/5] 生成回款数据...")
        generate_settlements(session, merchants, scenario_map, rng)

        print("\n[5/5] 生成保险和融资产品...")
        generate_insurance_and_financing(session, merchants, rng)

        print("\n[6/6] 生成 V3 风险案件与工作流数据...")
        generate_v3_data(session, merchants, scenario_map, rng)

        session.commit()
        print("\n✅ Mock 数据生成完成！")

        # 打印统计
        print(f"\n统计:")
        print(f"  商家: {session.query(Merchant).count()}")
        print(f"  订单: {session.query(Order).count()}")
        print(f"  退货: {session.query(Return).count()}")
        print(f"  回款: {session.query(Settlement).count()}")
        print(f"  保险: {session.query(InsurancePolicy).count()}")
        print(f"  融资产品: {session.query(FinancingProduct).count()}")

    except Exception as e:
        session.rollback()
        print(f"\n❌ 生成失败: {e}")
        raise
    finally:
        session.close()


def generate_v3_data(session, merchants, scenario_map, rng: random.Random):
    """生成 V3 风险案件、工作流运行、审批任务、Prompt版本等 mock 数据"""

    # 1. 生成风险案件 — 为场景A/B/C的商家创建案件
    risk_cases = []
    risk_merchants = [i for i, s in scenario_map.items() if s in ("A", "B", "C")]
    for mi in risk_merchants:
        merchant = merchants[mi]
        scenario = scenario_map[mi]
        level_map = {"A": "high", "B": "medium", "C": "high"}
        case = RiskCase(
            merchant_id=merchant.id,
            trigger_json=json.dumps({
                "type": "auto_monitor",
                "scenario": scenario,
                "return_rate_7d": round(rng.uniform(0.15, 0.35), 4),
                "settlement_delay_days": rng.randint(0, 8),
            }),
            risk_level=level_map.get(scenario, "medium"),
            risk_score=round(rng.uniform(40, 95), 2),
            status=rng.choice(["NEW", "ANALYZING", "ANALYZED", "REVIEWED"]),
        )
        session.add(case)
        risk_cases.append(case)
    session.flush()
    print(f"  ✓ 生成 {len(risk_cases)} 个风险案件")

    # 2. 生成工作流运行
    statuses = ["COMPLETED", "COMPLETED", "PAUSED", "PENDING_APPROVAL", "FAILED_RETRYABLE"]
    wf_runs = []
    agents = [
        "load_case_context", "triage_case", "compute_metrics",
        "forecast_gap", "collect_evidence", "diagnose_case",
        "generate_recommendations", "run_guardrails",
    ]
    for case in risk_cases:
        wf_status = rng.choice(statuses)
        run = WorkflowRun(
            case_id=case.id,
            graph_version="v3.0",
            status=wf_status,
            current_node=rng.choice(agents) if wf_status != "COMPLETED" else "write_audit_log",
            started_at=datetime.utcnow() - timedelta(hours=rng.randint(1, 48)),
            ended_at=datetime.utcnow() if wf_status == "COMPLETED" else None,
            paused_at=datetime.utcnow() if wf_status == "PAUSED" else None,
        )
        session.add(run)
        wf_runs.append(run)
    session.flush()
    print(f"  ✓ 生成 {len(wf_runs)} 个工作流运行")

    # 3. 生成 agent 运行记录
    agent_run_count = 0
    for run in wf_runs:
        node_count = rng.randint(3, len(agents))
        for i in range(node_count):
            ar = AgentRun(
                workflow_run_id=run.id,
                agent_name=agents[i],
                model_name="rule-based",
                prompt_version="1",
                schema_version="1",
                input_json="{}",
                output_json="{}",
                status="SUCCESS",
                latency_ms=rng.randint(10, 500),
            )
            session.add(ar)
            agent_run_count += 1
    session.flush()
    print(f"  ✓ 生成 {agent_run_count} 条 Agent 运行记录")

    # 4. 生成审批任务
    approval_types = ["business_loan", "advance_settlement", "fraud_review", "claim_submission"]
    approval_roles = ["finance_ops", "risk_ops", "claim_ops"]
    approval_statuses = ["PENDING", "PENDING", "APPROVED", "REJECTED"]
    approval_count = 0
    for run in wf_runs:
        if run.status in ("PAUSED", "PENDING_APPROVAL", "COMPLETED"):
            num_approvals = rng.randint(1, 3)
            for _ in range(num_approvals):
                task = ApprovalTask(
                    workflow_run_id=run.id,
                    case_id=run.case_id,
                    approval_type=rng.choice(approval_types),
                    assignee_role=rng.choice(approval_roles),
                    status=rng.choice(approval_statuses),
                    payload_json=json.dumps({"action": "mock_action", "amount": rng.randint(10000, 200000)}),
                    reviewer="admin" if rng.random() > 0.5 else None,
                    reviewed_at=datetime.utcnow() if rng.random() > 0.5 else None,
                    comment=rng.choice(["同意", "需要复核", "", None]),
                    due_at=datetime.utcnow() + timedelta(hours=rng.randint(4, 48)),
                )
                session.add(task)
                approval_count += 1
    session.flush()
    print(f"  ✓ 生成 {approval_count} 个审批任务")

    # 5. 生成 Prompt 版本
    agent_names = [
        "triage_agent", "diagnosis_agent", "forecast_agent",
        "recommendation_agent", "evidence_agent", "compliance_guard_agent",
        "execution_agent", "summary_agent",
    ]
    pv_count = 0
    for agent_name in agent_names:
        pv = PromptVersion(
            agent_name=agent_name,
            version="1",
            content=f"# {agent_name} 默认 Prompt\n\n你是{agent_name}，请根据输入数据执行分析。",
            status="ACTIVE",
            canary_weight=0.0,
        )
        session.add(pv)
        pv_count += 1
    session.flush()
    print(f"  ✓ 生成 {pv_count} 个 Prompt 版本")

    # 6. 生成 Schema 版本
    sv_count = 0
    for agent_name in agent_names:
        sv = SchemaVersion(
            agent_name=agent_name,
            version="1",
            json_schema=json.dumps({"type": "object", "description": f"{agent_name} output schema v1"}),
        )
        session.add(sv)
        sv_count += 1
    session.flush()
    print(f"  ✓ 生成 {sv_count} 个 Schema 版本")

    # 7. 生成评测数据集
    dataset = EvalDataset(
        name="V3 基准评测集",
        description="包含 10 个典型风险案例的评测数据集",
        test_cases_json=json.dumps([
            {"input": {"merchant_id": 1001, "risk_type": "cash_gap"}, "expected_output": {"risk_level": "high"}},
            {"input": {"merchant_id": 1002, "risk_type": "high_return"}, "expected_output": {"risk_level": "medium"}},
            {"input": {"merchant_id": 1003, "risk_type": "suspected_fraud"}, "expected_output": {"risk_level": "critical"}},
        ], ensure_ascii=False),
    )
    session.add(dataset)
    session.flush()
    print(f"  ✓ 生成 1 个评测数据集")


if __name__ == "__main__":
    main()
