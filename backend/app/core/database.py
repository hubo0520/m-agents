"""SQLAlchemy 数据库配置"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from loguru import logger

from app.core.config import settings

# 根据数据库类型条件设置连接参数
_engine_kwargs: dict = {}
if settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}  # SQLite 需要

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    **_engine_kwargs,
)

logger.info("数据库引擎初始化 | url={}", settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
