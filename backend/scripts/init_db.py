"""数据库初始化脚本 — 创建所有表和索引"""
import sys
import os

# 将 backend 目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, Base
from app.models.models import (  # noqa: F401 — 确保所有模型被导入
    Merchant, Order, Return, LogisticsEvent, Settlement,
    InsurancePolicy, FinancingProduct, RiskCase, EvidenceItem,
    Recommendation, Review, AuditLog,
)


def init_db():
    """创建所有表"""
    print("正在创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("数据库初始化完成！")

    # 列出已创建的表
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"已创建 {len(tables)} 张表: {', '.join(tables)}")


if __name__ == "__main__":
    init_db()
