"""
LLM 并发控制测试

测试信号量并发控制和排队超时机制。
"""
import threading
import time
import pytest


class TestLlmSemaphore:
    """LLM 信号量并发控制测试"""

    def test_semaphore_limits_concurrency(self):
        """信号量应限制并发数"""
        from app.core.llm_client import _llm_semaphore
        from app.core.config import settings

        # 信号量当前值应等于配置的最大并发数
        # 通过 acquire/release 验证
        acquired = []
        for _ in range(settings.LLM_MAX_CONCURRENCY):
            result = _llm_semaphore.acquire(timeout=0.1)
            acquired.append(result)

        # 所有都应成功获取
        assert all(acquired)

        # 再获取一个应该超时
        extra = _llm_semaphore.acquire(timeout=0.1)
        assert extra is False

        # 释放所有
        for _ in acquired:
            _llm_semaphore.release()

    def test_acquire_llm_semaphore_success(self):
        """正常获取信号量应返回等待耗时"""
        from app.core.llm_client import _acquire_llm_semaphore, _llm_semaphore

        wait_ms = _acquire_llm_semaphore(timeout=5)
        assert wait_ms >= 0
        _llm_semaphore.release()

    def test_acquire_llm_semaphore_timeout(self):
        """排队超时应抛出 LlmQueueTimeoutError"""
        from app.core.llm_client import _acquire_llm_semaphore, _llm_semaphore
        from app.core.exceptions import LlmQueueTimeoutError
        from app.core.config import settings

        # 先占满所有信号量
        for _ in range(settings.LLM_MAX_CONCURRENCY):
            _llm_semaphore.acquire(timeout=1)

        try:
            # 此时获取应超时
            with pytest.raises(LlmQueueTimeoutError):
                _acquire_llm_semaphore(timeout=1)
        finally:
            # 释放所有
            for _ in range(settings.LLM_MAX_CONCURRENCY):
                _llm_semaphore.release()
