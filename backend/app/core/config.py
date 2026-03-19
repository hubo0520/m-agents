"""全局配置"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data.db')}"

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

    # LLM 配置
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    OPENAI_MODEL: str = "qwen-plus"
    USE_LLM: bool = True

    # 经营贷资格
    MIN_OPERATION_DAYS: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
