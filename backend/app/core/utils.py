"""
通用工具函数
"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """获取当前 UTC 时间（timezone-naive），与 MySQL DATETIME 列兼容。
    MySQL 的 DATETIME 类型不携带时区信息（naive），若 Python 端使用
    timezone-aware datetime 做减法/比较，会触发 TypeError。
    因此统一返回 naive UTC datetime。
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
