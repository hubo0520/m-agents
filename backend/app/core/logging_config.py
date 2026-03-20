"""
统一日志配置模块

配置 loguru 日志框架，支持环境变量控制日志级别和格式。
"""

import os
import sys
from loguru import logger


def setup_logging():
    """
    配置 loguru 日志框架
    
    支持的环境变量：
    - LOG_LEVEL: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL），默认 INFO
    - LOG_FORMAT: 日志格式（simple, json, detailed），默认 simple
    """
    
    # 获取配置
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "simple").lower()
    
    # 移除默认处理器
    logger.remove()
    
    # 定义日志格式
    if log_format == "json":
        # JSON 格式，适合结构化日志处理
        format_str = (
            '{"time": "{time:YYYY-MM-DD HH:mm:ss.SSS}", '
            '"level": "{level}", '
            '"name": "{name}", '
            '"function": "{function}", '
            '"line": {line}, '
            '"trace_id": "{extra[trace_id]}", '
            '"message": "{message}"'
            '}'
        )
    elif log_format == "detailed":
        # 详细格式，包含更多上下文信息
        format_str = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<dim>{extra[trace_id]}</dim> | "
            "<level>{message}</level>"
        )
    else:
        # 简单格式（默认）
        format_str = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan> | "
            "<level>{message}</level>"
        )
    
    # 添加控制台处理器
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
    
    # 添加文件处理器（可选，可根据需要启用）
    # log_file = os.getenv("LOG_FILE", "app.log")
    # logger.add(
    #     log_file,
    #     level=log_level,
    #     format=format_str,
    #     rotation="10 MB",
    #     retention="30 days",
    #     compression="gz",
    # )
    
    # 配置第三方库日志级别
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