"""
PromptLoader 单元测试
"""
import time
import pytest
from unittest.mock import patch, MagicMock


class TestPromptLoader:
    """PromptLoader 加载、缓存、灰度分流、fallback 测试"""

    def setup_method(self):
        """每个测试前清除缓存"""
        from app.core.prompt_loader import PromptLoader
        PromptLoader.invalidate_cache()

    def test_fallback_to_default_when_db_empty(self):
        """DB 无记录时 fallback 到默认 Prompt"""
        from app.core.prompt_loader import PromptLoader

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.core.prompt_loader.PromptLoader._load_from_db", return_value=(None, "")):
            content, version = PromptLoader.load("test_agent", default="默认 Prompt 内容")

        assert content == "默认 Prompt 内容"
        assert version == "default"

    def test_load_active_version_from_db(self):
        """从 DB 加载 ACTIVE 版本"""
        from app.core.prompt_loader import PromptLoader

        with patch("app.core.prompt_loader.PromptLoader._load_from_db", return_value=("DB Prompt 内容", "3")):
            content, version = PromptLoader.load("test_agent", default="默认")

        assert content == "DB Prompt 内容"
        assert version == "3"

    def test_cache_ttl_works(self):
        """缓存 TTL 机制验证"""
        from app.core.prompt_loader import PromptLoader, _cache

        # 首次加载
        with patch("app.core.prompt_loader.PromptLoader._load_from_db", return_value=("v1 内容", "1")) as mock_load:
            content1, _ = PromptLoader.load("test_agent", default="默认")
            assert content1 == "v1 内容"

        # 第二次加载（命中缓存，不查 DB）
        with patch("app.core.prompt_loader.PromptLoader._load_from_db", return_value=("v2 内容", "2")) as mock_load:
            content2, _ = PromptLoader.load("test_agent", default="默认")
            assert content2 == "v1 内容"  # 应该是缓存值
            mock_load.assert_not_called()  # 不应该查 DB

    def test_cache_invalidation(self):
        """缓存清除验证"""
        from app.core.prompt_loader import PromptLoader

        with patch("app.core.prompt_loader.PromptLoader._load_from_db", return_value=("v1 内容", "1")):
            PromptLoader.load("agent_a", default="默认")

        # 清除单个
        PromptLoader.invalidate_cache("agent_a")
        with patch("app.core.prompt_loader.PromptLoader._load_from_db", return_value=("v2 内容", "2")) as mock_load:
            content, _ = PromptLoader.load("agent_a", default="默认")
            assert content == "v2 内容"

    def test_canary_weight_routing(self):
        """灰度分流验证：canary_weight=1.0 时应 100% 命中灰度版本"""
        from app.core.prompt_loader import PromptLoader

        mock_active = MagicMock()
        mock_active.content = "ACTIVE 内容"
        mock_active.version = "1"
        mock_active.canary_weight = 0.0

        mock_canary = MagicMock()
        mock_canary.content = "CANARY 内容"
        mock_canary.version = "2"
        mock_canary.canary_weight = 1.0  # 100% 灰度

        mock_db = MagicMock()

        def mock_filter(*args, **kwargs):
            return mock_db.query.return_value.filter.return_value
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_active, mock_canary]

        content, version = PromptLoader._load_from_db(mock_db, "test_agent")
        assert content == "CANARY 内容"
        assert version == "2"

    def test_db_exception_fallback(self):
        """DB 异常时优雅 fallback 到默认 Prompt"""
        from app.core.prompt_loader import PromptLoader

        with patch("app.core.database.SessionLocal", side_effect=Exception("DB 连接失败")):
            content, version = PromptLoader.load("test_agent", default="安全默认值")

        assert content == "安全默认值"
        assert version == "default"
