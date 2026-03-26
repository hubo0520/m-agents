"""
LLM 客户端 — 统一封装 OpenAI 调用

所有 Agent 通过此模块调用 LLM，确保 OPENAI_BASE_URL / API_KEY / MODEL 统一管理。
"""
from dataclasses import dataclass, asdict
from typing import Callable, Optional, Type, TypeVar
import time
import threading

from pydantic import BaseModel
from loguru import logger

from app.core.config import settings

T = TypeVar("T", bound=BaseModel)

# 懒加载 OpenAI 客户端（仅在 USE_LLM=True 时初始化）
_client = None

# LLM 并发控制信号量
_llm_semaphore = threading.Semaphore(settings.LLM_MAX_CONCURRENCY)
_llm_waiting_count = 0
_llm_waiting_lock = threading.Lock()


def _acquire_llm_semaphore(timeout: Optional[int] = None) -> float:
    """
    获取 LLM 信号量，返回等待耗时（毫秒）。
    超时则抛出 LlmQueueTimeoutError。
    """
    global _llm_waiting_count
    timeout = timeout or settings.LLM_QUEUE_TIMEOUT

    with _llm_waiting_lock:
        _llm_waiting_count += 1
        waiting = _llm_waiting_count

    if waiting > 1:
        logger.info("LLM 排队中 | 当前等待数={}", waiting)

    wait_start = time.time()
    acquired = _llm_semaphore.acquire(timeout=timeout)
    wait_ms = int((time.time() - wait_start) * 1000)

    with _llm_waiting_lock:
        _llm_waiting_count -= 1

    if not acquired:
        from app.core.exceptions import LlmQueueTimeoutError
        logger.error("LLM 排队超时 | timeout={}s | wait_ms={}", timeout, wait_ms)
        raise LlmQueueTimeoutError(
            detail=f"LLM 服务繁忙，排队等待 {timeout} 秒后超时",
            extra={"wait_ms": wait_ms, "timeout": timeout},
        )

    if wait_ms > 100:
        logger.info("LLM 信号量获取成功 | wait_ms={}", wait_ms)

    return wait_ms


def _get_client():
    """获取 OpenAI 客户端（懒加载单例）"""
    global _client
    if _client is None:
        try:
            import httpx
            from openai import OpenAI
            _client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                timeout=httpx.Timeout(60.0, connect=10.0),  # 读取 60s / 连接 10s
            )
            logger.info(
                "OpenAI 客户端初始化成功 | base_url=%s | model=%s",
                settings.OPENAI_BASE_URL,
                settings.OPENAI_MODEL,
            )
        except ImportError:
            raise RuntimeError(
                "openai 包未安装。请执行: pip install openai>=1.0.0"
            )
        except Exception as e:
            raise RuntimeError(f"OpenAI 客户端初始化失败: {e}")
    return _client


def chat_completion(
    messages: list[dict],
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """
    基础聊天补全调用。

    Args:
        messages: OpenAI 消息列表 [{"role": "system", "content": "..."}]
        model: 模型名称，默认使用 config 中的 OPENAI_MODEL
        temperature: 温度参数
        max_tokens: 最大 token 数

    Returns:
        LLM 回复文本
    """
    client = _get_client()
    wait_ms = _acquire_llm_semaphore()
    try:
        t0 = time.time()
        response = client.chat.completions.create(
            model=model or settings.OPENAI_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        elapsed_ms = int((time.time() - t0) * 1000)
        content = response.choices[0].message.content
        logger.info("LLM 调用完成 | model={} | elapsed_ms={} | queue_wait_ms={}", model or settings.OPENAI_MODEL, elapsed_ms, wait_ms)
        return content if content is not None else ""
    finally:
        _llm_semaphore.release()


def chat_completion_stream(
    messages: list[dict],
    on_chunk: Optional[Callable[[str], None]] = None,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """
    流式聊天补全调用 — 逐 chunk 返回大模型回复。

    Args:
        messages: OpenAI 消息列表
        on_chunk: 每收到一个 chunk 时调用的回调，传入 delta text；为 None 时等价于非流式调用
        model: 模型名称，默认使用 config 中的 OPENAI_MODEL
        temperature: 温度参数
        max_tokens: 最大 token 数

    Returns:
        完整的 LLM 回复文本（所有 chunk 拼接）
    """
    # on_chunk 为 None 时退化为非流式调用
    if on_chunk is None:
        return chat_completion(messages, model, temperature, max_tokens)

    client = _get_client()
    wait_ms = _acquire_llm_semaphore()
    try:
        stream = client.chat.completions.create(
            model=model or settings.OPENAI_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        full_content = ""
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                full_content += delta.content
                try:
                    on_chunk(delta.content)
                except Exception as e:
                    logger.warning("on_chunk 回调异常: %s", e)

        return full_content
    finally:
        _llm_semaphore.release()


def structured_output(
    messages: list[dict],
    response_model: Type[T],
    model: Optional[str] = None,
    temperature: float = 0.2,
) -> T:
    """
    结构化输出调用 — 让 LLM 直接输出 Pydantic 模型。

    使用 OpenAI 的 response_format 功能（需要 openai>=1.40 + 兼容模型）。
    若 LLM 不支持 structured output，则回退到 JSON 模式手动解析。

    Args:
        messages: OpenAI 消息列表
        response_model: Pydantic 模型类
        model: 模型名称
        temperature: 温度参数

    Returns:
        解析后的 Pydantic 模型实例
    """
    client = _get_client()
    wait_ms = _acquire_llm_semaphore()
    try:
        try:
            # 优先尝试 beta.chat.completions.parse（OpenAI Structured Outputs）
            response = client.beta.chat.completions.parse(
                model=model or settings.OPENAI_MODEL,
                messages=messages,
                response_format=response_model,
                temperature=temperature,
            )
            parsed = response.choices[0].message.parsed
            if parsed is not None:
                return parsed
        except Exception as e:
            logger.warning("Structured Output 解析失败，回退到 JSON 模式: %s", e)

        # 回退：使用 JSON 模式 + 手动解析
        import json
        messages_with_schema = messages.copy()
        schema_hint = json.dumps(response_model.model_json_schema(), ensure_ascii=False)
        messages_with_schema.append({
            "role": "user",
            "content": f"请严格按以下 JSON Schema 输出，不要输出其他内容:\n{schema_hint}",
        })

        response = client.chat.completions.create(
            model=model or settings.OPENAI_MODEL,
            messages=messages_with_schema,
            temperature=temperature,
            response_format={"type": "json_object"},
        )

        raw_json = response.choices[0].message.content
        return response_model.model_validate_json(raw_json)
    finally:
        _llm_semaphore.release()


def is_llm_enabled() -> bool:
    """检查 LLM 是否启用"""
    return settings.USE_LLM and bool(settings.OPENAI_API_KEY)


def load_prompt(agent_name: str, default: str = "") -> tuple[str, str]:
    """
    加载指定 Agent 的 Prompt 版本（从 DB 或 fallback 到默认值）。

    Args:
        agent_name: Agent 名称，如 "diagnosis_agent"
        default: 默认 Prompt 内容

    Returns:
        (prompt_content, version_str) 元组
    """
    from app.core.prompt_loader import PromptLoader
    return PromptLoader.load(agent_name, default)


# ═══════════════════════════════════════════════════════════════
# LLM 事件数据类（用于 Agent → SSE 推送链路）
# ═══════════════════════════════════════════════════════════════

@dataclass
class LlmEvent:
    """
    LLM 交互事件 — 在 Agent 调用 LLM 的过程中产生，
    通过回调链透传到 SSE 端点推送给前端。
    """
    event_type: str           # "llm_input" | "llm_chunk" | "llm_done"
    agent_name: str           # Agent 名称，如 "summary_agent"
    step: str                 # 对应的工作流步骤，如 "finalize_summary"
    content: str = ""         # 事件内容（chunk delta / 完整回复）
    elapsed_ms: int = 0       # 耗时（仅 llm_done 时有值）
    system_prompt: str = ""   # System prompt（仅 llm_input 时有值）
    user_prompt: str = ""     # User prompt（仅 llm_input 时有值）

    def to_dict(self) -> dict:
        return asdict(self)