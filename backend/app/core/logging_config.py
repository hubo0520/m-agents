"""
统一日志配置模块

配置 loguru 日志框架，支持环境变量控制日志级别、格式和文件存储。

支持的环境变量：
- LOG_LEVEL: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL），默认 INFO
- LOG_FORMAT: 日志格式（simple, json, detailed），默认 simple
- LOG_FILE_ENABLED: 是否启用文件日志（true / false），默认 true
- LOG_DIR: 日志目录路径，默认 backend/logs/
- LOG_ROTATION_SIZE: 单文件滚动大小，默认 50 MB
- LOG_RETENTION_SIZE: 日志目录总大小上限，默认 1 GB
- LOG_COMPRESSION: 压缩格式（gz / 空字符串禁用），默认 gz
"""

import os
import sys
from pathlib import Path
from loguru import logger


def _parse_size_to_bytes(size_str: str) -> int:
    """
    将人类可读的大小字符串解析为字节数。
    支持格式如 '50 MB', '1 GB', '500MB' 等。
    """
    size_str = size_str.strip().upper()
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    for unit, multiplier in sorted(units.items(), key=lambda x: -len(x[0])):
        if size_str.endswith(unit):
            number_str = size_str[: -len(unit)].strip()
            return int(float(number_str) * multiplier)
    # 没有单位，当作字节
    return int(size_str)


def _make_retention_by_total_size(log_dir: str, max_total_bytes: int):
    """
    创建自定义 retention 函数：扫描日志目录总大小，
    超过 max_total_bytes 时按修改时间升序删除最旧文件。

    loguru 的 retention 回调签名：retention(list_of_log_files)
    """
    def _retention_func(files):
        log_path = Path(log_dir)
        # 收集日志目录下所有日志文件（含压缩文件）
        all_log_files = sorted(
            [f for f in log_path.iterdir() if f.is_file()],
            key=lambda f: f.stat().st_mtime,  # 按修改时间升序
        )
        # 计算当前总大小
        total_size = sum(f.stat().st_size for f in all_log_files)
        # 从最旧的文件开始删除，直到总大小低于上限
        for f in all_log_files:
            if total_size <= max_total_bytes:
                break
            # 不要删除当前正在写入的日志文件（app.log）
            if f.name == "app.log":
                continue
            try:
                fsize = f.stat().st_size
                f.unlink()
                total_size -= fsize
            except OSError:
                pass  # 文件可能正在被使用，跳过

    return _retention_func


def setup_logging():
    """
    配置 loguru 日志框架：控制台 + 可选文件 Sink
    """

    # ── 基础配置 ──
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "simple").lower()

    # ── 文件日志配置 ──
    log_file_enabled = os.getenv("LOG_FILE_ENABLED", "true").lower() == "true"
    log_dir = os.getenv("LOG_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
    log_rotation_size = os.getenv("LOG_ROTATION_SIZE", "50 MB")
    log_retention_size = os.getenv("LOG_RETENTION_SIZE", "1 GB")
    log_compression = os.getenv("LOG_COMPRESSION", "gz") or None  # 空字符串 → None（禁用压缩）

    # 移除默认处理器
    logger.remove()

    # ── 定义控制台日志格式 ──
    if log_format == "json":
        format_str = (
            '{{"time": "{time:YYYY-MM-DD HH:mm:ss.SSS}", '
            '"level": "{level}", '
            '"name": "{name}", '
            '"function": "{function}", '
            '"line": {line}, '
            '"trace_id": "{extra[trace_id]}", '
            '"message": "{message}"'
            '}}'
        )
    elif log_format == "detailed":
        format_str = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<dim>{extra[trace_id]}</dim> | "
            "<level>{message}</level>"
        )
    else:
        format_str = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan> | "
            "<level>{message}</level>"
        )

    # ── 添加控制台处理器 ──
    logger.add(
        sys.stderr,
        level=log_level,
        format=format_str,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # 配置默认 extra 字段（避免 KeyError）
    logger.configure(extra={"trace_id": "-"})

    # ── 添加文件处理器 ──
    if log_file_enabled:
        # 确保日志目录存在（含中间目录）
        log_dir = os.path.abspath(log_dir)
        os.makedirs(log_dir, exist_ok=True)

        # 文件日志使用 detailed 格式（人类可读，无 ANSI 颜色码）
        file_format_str = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "trace_id={extra[trace_id]} | "
            "{message}"
        )

        # 解析 retention 总大小上限
        max_total_bytes = _parse_size_to_bytes(log_retention_size)
        retention_func = _make_retention_by_total_size(log_dir, max_total_bytes)

        log_file_path = os.path.join(log_dir, "app.log")
        logger.add(
            log_file_path,
            level=log_level,
            format=file_format_str,
            rotation=log_rotation_size,      # 单文件达到此大小时滚动
            retention=retention_func,         # 自定义：按总目录大小清理
            compression=log_compression,      # 滚动后自动压缩（默认 gz）
            colorize=False,                   # 文件不含 ANSI 颜色码
            backtrace=True,
            diagnose=True,
            encoding="utf-8",
        )

    # ── 配置第三方库日志级别 ──
    # 降低第三方库的日志噪音
    try:
        logger.level("HTTPCORE", no=15)
    except ValueError:
        pass  # 级别已存在，忽略
    try:
        logger.level("HTTPX", no=15)
    except ValueError:
        pass
    try:
        logger.level("OPENAI", no=20)
    except ValueError:
        pass

    return logger


# 初始化日志配置
logger = setup_logging()


# 提供便捷的日志函数
def get_logger(name: str = None):
    """获取指定名称的日志器"""
    if name:
        return logger.bind(name=name)
    return logger


def bind_trace_id(trace_id: str):
    """绑定 trace_id 到当前日志上下文，便于请求链路追踪"""
    return logger.bind(trace_id=trace_id)