"""
LLM 客户端 — 统一封装 OpenAI 调用

所有 Agent 通过此模块调用 LLM，确保 OPENAI_BASE_URL / API_KEY / MODEL 统一管理。
"""
import logging
from typing import Optional, Type, TypeVar

from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# 懒加载 OpenAI 客户端（仅在 USE_LLM=True 时初始化）
_client = None


def _get_client():
    """获取 OpenAI 客户端（懒加载单例）"""
    global _client
    if _client is None:
        try:
            from openai import OpenAI
            _client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,  # ← 这里实际使用了 OPENAI_BASE_URL
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
    response = client.chat.completions.create(
        model=model or settings.OPENAI_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content
    return content if content is not None else ""


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


def is_llm_enabled() -> bool:
    """检查 LLM 是否启用"""
    return settings.USE_LLM and bool(settings.OPENAI_API_KEY)
