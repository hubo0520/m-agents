"""
风险案件生成脚本

使用方法：
    python scripts/generate_risk_cases.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.services.risk_scanner import generate_risk_cases
from app.agents.orchestrator import analyze as agent_analyze
from app.services.task_generator import generate_tasks_for_case


def main():
    print("开始扫描商家并生成风险案件...\n")
    session = SessionLocal()

    try:
        cases = generate_risk_cases(session)
        session.commit()

        print(f"\n✅ 生成 {len(cases)} 条风险案件:")
        for c in cases:
            print(f"  - 案件 #{c.id}: 商家 #{c.merchant_id}, "
                  f"风险等级={c.risk_level}, 分数={c.risk_score}, "
                  f"状态={c.status}")

        # 统计
        high_count = sum(1 for c in cases if c.risk_level == "high")
        medium_count = sum(1 for c in cases if c.risk_level == "medium")
        low_count = sum(1 for c in cases if c.risk_level == "low")
        print(f"\n统计: High={high_count}, Medium={medium_count}, Low={low_count}")

        # V2: 对所有案件运行 Agent 分析 + 任务生成
        print("\n[V2] 运行 Agent 分析并生成执行任务...")
        total_tasks = 0
        for c in cases:
            try:
                # 运行 Agent 分析（内部会自动调用任务生成引擎）
                agent_analyze(session, c.id)
                session.commit()

                # 统计该案件生成的任务数
                tasks = generate_tasks_for_case(session, c.id)
                session.commit()
                total_tasks += len(tasks)
                if tasks:
                    print(f"  案件 #{c.id}: 生成 {len(tasks)} 条执行任务 -> "
                          f"{', '.join(t['task_type'] for t in tasks)}")
            except Exception as e:
                session.rollback()
                print(f"  ⚠️ 案件 #{c.id} 分析/任务生成失败: {e}")

        print(f"\n✅ 总共生成 {total_tasks} 条执行任务")

    except Exception as e:
        session.rollback()
        print(f"\n❌ 生成失败: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
