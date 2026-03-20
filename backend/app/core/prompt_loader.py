"""
Prompt 版本运行时加载器

从 prompt_versions 表加载 ACTIVE 版本，支持灰度分流和内存缓存。
Agent 运行时通过此模块获取 Prompt，而非使用硬编码字符串。
"""
import random
import time
from typing import Optional, Dict, Tuple
from loguru import logger


# 内存缓存: {agent_name: (prompt_content, version_str, timestamp)}
_cache: Dict[str, Tuple[str, str, float]] = {}
_CACHE_TTL = 60  # 缓存 TTL 秒数


class PromptLoader:
    """Prompt 版本运行时加载器"""

    @staticmethod
    def load(agent_name: str, default: str = "") -> Tuple[str, str]:
        """
        加载指定 Agent 的 Prompt 版本。

        加载逻辑：
        1. 查询 DB 中该 Agent 的 ACTIVE 版本
        2. 如果有 canary_weight > 0 的 DRAFT 版本，按概率分流
        3. 如果 DB 中无记录，fallback 到代码中的默认 Prompt
        4. 缓存 Prompt 内容（TTL 60s），避免每次 Agent 调用都查库

        Args:
            agent_name: Agent 名称，如 "diagnosis_agent"
            default: 默认 Prompt 内容（DB 无记录时使用）

        Returns:
            (prompt_content, version_str) 元组
        """
        # 检查缓存
        now = time.time()
        if agent_name in _cache:
            content, version, cached_at = _cache[agent_name]
            if now - cached_at < _CACHE_TTL:
                return content, version

        # 查询 DB
        try:
            from app.core.database import SessionLocal
            db = SessionLocal()
            try:
                content, version = PromptLoader._load_from_db(db, agent_name)
                if content is not None:
                    _cache[agent_name] = (content, version, now)
                    return content, version
            finally:
                db.close()
        except Exception as e:
            logger.warning("从 DB 加载 Prompt 失败 (agent=%s)，使用默认版本: %s", agent_name, e)

        # Fallback 到默认 Prompt
        logger.info("Agent %s 使用默认硬编码 Prompt", agent_name)
        _cache[agent_name] = (default, "default", now)
        return default, "default"

    @staticmethod
    def _load_from_db(db, agent_name: str) -> Tuple[Optional[str], str]:
        """
        从 DB 加载 Prompt 版本，支持灰度分流。

        Returns:
            (content, version) 或 (None, "") 如果 DB 中无记录
        """
        from app.models.models import PromptVersion

        # 获取 ACTIVE 版本
        active = db.query(PromptVersion).filter(
            PromptVersion.agent_name == agent_name,
            PromptVersion.status == "ACTIVE",
        ).first()

        # 获取灰度 DRAFT 版本
        canary = db.query(PromptVersion).filter(
            PromptVersion.agent_name == agent_name,
            PromptVersion.status == "DRAFT",
            PromptVersion.canary_weight > 0,
        ).first()

        if not active and not canary:
            return None, ""

        # 灰度分流
        if canary and canary.canary_weight and canary.canary_weight > 0:
            if random.random() < canary.canary_weight:
                logger.info(
                    "Agent %s 命中灰度版本 v%s (canary_weight=%.2f)",
                    agent_name, canary.version, canary.canary_weight,
                )
                return canary.content, canary.version

        if active:
            return active.content, active.version

        # 只有 canary 没有 active 的情况（概率未命中灰度）
        if canary:
            return canary.content, canary.version

        return None, ""

    @staticmethod
    def invalidate_cache(agent_name: str = None):
        """
        清除缓存。

        Args:
            agent_name: 指定 Agent 名称清除；None 时清除所有缓存
        """
        global _cache
        if agent_name:
            _cache.pop(agent_name, None)
        else:
            _cache.clear()
        logger.debug("Prompt 缓存已清除: %s", agent_name or "全部")
