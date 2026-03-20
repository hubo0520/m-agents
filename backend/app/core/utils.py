"""
通用工具函数
"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """获取当前 UTC 时间（timezone-aware），替代已废弃的 datetime.utcnow()"""
    return datetime.now(timezone.utc)
