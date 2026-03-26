"""全局配置"""
from pydantic_settings import BaseSettings
from pydantic import model_validator, ConfigDict
from typing import List
import os


class Settings(BaseSettings):
    # 数据库（默认 MySQL）
    DATABASE_URL: str = "mysql+pymysql://root:Hjb0520+-@localhost:3306/m_agents"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # 风险阈值配置
    RETURN_RATE_AMPLIFICATION_THRESHOLD: float = 1.6
    PREDICTED_GAP_THRESHOLD: float = 50000.0
    SETTLEMENT_DELAY_THRESHOLD: float = 3.0
    ANOMALY_SCORE_THRESHOLD: float = 0.8

    # 风险等级阈值
    HIGH_RISK_AMPLIFICATION: float = 1.6
    HIGH_RISK_GAP: float = 50000.0
    HIGH_RISK_ANOMALY: float = 0.8
    MEDIUM_RISK_AMPLIFICATION: float = 1.3
    MEDIUM_RISK_DELAY: float = 2.0

    # LLM 配置（从 .env 文件读取）
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    OPENAI_MODEL: str = "qwen-plus"
    USE_LLM: bool = True

    # JWT 认证（从 .env 文件读取，务必使用强随机密钥）
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 调试模式（开启后允许 Header 传角色）
    DEBUG_AUTH: bool = True

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "simple"
    LOG_FILE_ENABLED: bool = True          # 是否启用文件日志
    LOG_DIR: str = "logs"                   # 日志目录路径
    LOG_ROTATION_SIZE: str = "50 MB"        # 单文件滚动大小
    LOG_RETENTION_SIZE: str = "1 GB"        # 日志目录总大小上限
    LOG_COMPRESSION: str = "gz"             # 压缩格式（空字符串禁用）

    # 经营贷资格
    MIN_OPERATION_DAYS: int = 60

    # 向量存储（RAG 对话系统）
    VECTOR_STORE_DIR: str = ""  # 空字符串使用默认路径 backend/vector_data/
    EMBEDDING_MODEL: str = "text-embedding-v4"  # 阿里云通义嵌入模型
    EMBEDDING_BATCH_SIZE: int = 6               # 嵌入请求批量大小（text-embedding-v4 限制较严，建议 ≤6）
    RAG_TOP_K: int = 5                          # 语义检索返回的最相关文档数

    # API 限流配置
    RATE_LIMIT_DEFAULT: int = 120         # 普通 API 每分钟最大请求数
    RATE_LIMIT_ANALYSIS: int = 5          # 分析类 API 每分钟最大请求数
    RATE_LIMIT_AUTH: int = 20             # 认证类 API（登录/注册）每分钟最大请求数

    # LLM 并发控制
    LLM_MAX_CONCURRENCY: int = 3          # LLM 最大并发调用数
    LLM_QUEUE_TIMEOUT: int = 120          # LLM 排队等待超时（秒）

    # 通知配置
    NOTIFICATION_POLL_INTERVAL: int = 30  # 前端轮询间隔（秒），仅用于文档说明

    @model_validator(mode="after")
    def _validate_security(self) -> "Settings":
        """安全校验：非调试模式下 JWT 密钥必须有效"""
        if not self.DEBUG_AUTH and len(self.JWT_SECRET_KEY) < 32:
            raise ValueError(
                "JWT_SECRET_KEY 必须至少 32 个字符（当前长度 %d）。"
                "如需跳过校验，请设置 DEBUG_AUTH=True" % len(self.JWT_SECRET_KEY)
            )
        return self

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
