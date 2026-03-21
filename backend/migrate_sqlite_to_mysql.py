#!/usr/bin/env python3
"""
SQLite → MySQL 数据迁移脚本
用法: python migrate_sqlite_to_mysql.py
"""
import os
import sys
import sqlite3
from datetime import datetime

import pymysql
from sqlalchemy import create_engine, MetaData, text, inspect

# ── 配置 ──────────────────────────────────────────────
SQLITE_PATH = os.path.join(os.path.dirname(__file__), "data.db")
# 将 localhost 改为你的服务器公网 IP
MYSQL_URL = "mysql+pymysql://root:Hjb0520+-@47.103.5.199:3306/m_agents"
BATCH_SIZE = 2000  # 每批插入行数

# ── 按外键依赖排列的表顺序（父表在前、子表在后）──
TABLE_ORDER = [
    "users",
    "merchants",
    "schema_versions",
    "financing_products",
    "risk_cases",
    "orders",
    "returns",
    "settlements",
    "reviews",
    "insurance_policies",
    "claims",
    "logistics_events",
    "financing_applications",
    "evidence_items",
    "workflow_runs",
    "agent_runs",
    "tool_invocations",
    "recommendations",
    "approval_tasks",
    "manual_reviews",
    "audit_logs",
    "eval_datasets",
    "eval_runs",
    "eval_results",
    "prompt_versions",
    "conversations",
    "conversation_messages",
    "checkpoints",
]


def get_sqlite_rows(sqlite_conn, table_name):
    """从 SQLite 读取整张表数据，返回 (列名列表, 行数据列表)"""
    cursor = sqlite_conn.execute(f"SELECT * FROM [{table_name}]")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    return columns, rows


def chunked(lst, size):
    """将列表按 size 分块"""
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def migrate():
    print("=" * 60)
    print("  SQLite → MySQL 数据迁移")
    print("=" * 60)

    # 检查 SQLite 文件
    if not os.path.exists(SQLITE_PATH):
        print(f"❌ 找不到 SQLite 文件: {SQLITE_PATH}")
        sys.exit(1)

    # 连接
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    mysql_engine = create_engine(MYSQL_URL, echo=False)

    # 获取 MySQL 中已有的表
    mysql_tables = set(inspect(mysql_engine).get_table_names())

    # 获取 SQLite 中的表
    sqlite_tables = set(
        row[0] for row in sqlite_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    )

    print(f"\n📂 SQLite 文件: {SQLITE_PATH}")
    print(f"📊 SQLite 表数: {len(sqlite_tables)}")
    print(f"🗄️  MySQL 表数:  {len(mysql_tables)}")

    # 按依赖顺序迁移
    migrated = 0
    skipped = 0
    total_rows = 0

    with mysql_engine.connect() as conn:
        # 临时禁用外键检查，加速导入
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        conn.execute(text("SET UNIQUE_CHECKS = 0"))

        for table_name in TABLE_ORDER:
            if table_name not in sqlite_tables:
                print(f"  ⏭️  {table_name:<30} — SQLite 中不存在，跳过")
                skipped += 1
                continue

            if table_name not in mysql_tables:
                print(f"  ⏭️  {table_name:<30} — MySQL 中不存在，跳过")
                skipped += 1
                continue

            # 检查 MySQL 表是否已有数据
            existing = conn.execute(text(f"SELECT COUNT(*) FROM `{table_name}`")).scalar()
            if existing > 0:
                print(f"  ⚠️  {table_name:<30} — MySQL 已有 {existing} 行，跳过（避免重复）")
                skipped += 1
                continue

            # 读取 SQLite 数据
            columns, rows = get_sqlite_rows(sqlite_conn, table_name)
            if not rows:
                print(f"  ⏭️  {table_name:<30} — 空表，跳过")
                skipped += 1
                continue

            # 构造 INSERT 语句
            col_list = ", ".join(f"`{c}`" for c in columns)
            placeholders = ", ".join(f":{c}" for c in columns)
            insert_sql = text(f"INSERT INTO `{table_name}` ({col_list}) VALUES ({placeholders})")

            # 分批插入
            row_count = 0
            for batch in chunked(rows, BATCH_SIZE):
                # 转为字典列表
                dict_rows = []
                for row in batch:
                    d = {}
                    for i, col in enumerate(columns):
                        val = row[i]
                        # SQLite 的 None 在 MySQL 中保持 NULL
                        d[col] = val
                    dict_rows.append(d)

                conn.execute(insert_sql, dict_rows)
                row_count += len(batch)

            conn.commit()
            total_rows += row_count
            migrated += 1
            print(f"  ✅ {table_name:<30} — {row_count:>6} 行已导入")

        # 处理不在预定义顺序中的额外表
        extra_tables = sqlite_tables - set(TABLE_ORDER)
        for table_name in sorted(extra_tables):
            if table_name not in mysql_tables:
                print(f"  ⏭️  {table_name:<30} — MySQL 中不存在，跳过")
                continue

            existing = conn.execute(text(f"SELECT COUNT(*) FROM `{table_name}`")).scalar()
            if existing > 0:
                print(f"  ⚠️  {table_name:<30} — MySQL 已有 {existing} 行，跳过")
                continue

            columns, rows = get_sqlite_rows(sqlite_conn, table_name)
            if not rows:
                continue

            col_list = ", ".join(f"`{c}`" for c in columns)
            placeholders = ", ".join(f":{c}" for c in columns)
            insert_sql = text(f"INSERT INTO `{table_name}` ({col_list}) VALUES ({placeholders})")

            row_count = 0
            for batch in chunked(rows, BATCH_SIZE):
                dict_rows = [{columns[i]: row[i] for i in range(len(columns))} for row in batch]
                conn.execute(insert_sql, dict_rows)
                row_count += len(batch)

            conn.commit()
            total_rows += row_count
            migrated += 1
            print(f"  ✅ {table_name:<30} — {row_count:>6} 行已导入（额外表）")

        # 恢复检查
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        conn.execute(text("SET UNIQUE_CHECKS = 1"))
        conn.commit()

    sqlite_conn.close()

    # 汇总
    print("\n" + "=" * 60)
    print(f"  ✅ 迁移完成！")
    print(f"  📊 迁移表数: {migrated}")
    print(f"  ⏭️  跳过表数: {skipped}")
    print(f"  📝 总导入行数: {total_rows:,}")
    print("=" * 60)


if __name__ == "__main__":
    migrate()
