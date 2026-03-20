"""
对话式分析 API — 案件对话管理与 SSE 流式对话
"""
import json
import asyncio
import time as _time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.models.models import (
    Conversation, ConversationMessage, RiskCase, EvidenceItem,
)
from app.core.llm_client import chat_completion, chat_completion_stream, is_llm_enabled

router = APIRouter(prefix="/api", tags=["对话式分析"])


# ───────────── Pydantic Schemas ─────────────

class CreateConversationRequest(BaseModel):
    title: str = "新对话"


class ChatMessageRequest(BaseModel):
    message: str


class ConversationResponse(BaseModel):
    id: int
    case_id: int
    title: str
    message_count: int
    created_at: str | None
    updated_at: str | None


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: str | None


# ───────────── POST /api/cases/{case_id}/conversations ─────────────

@router.post("/cases/{case_id}/conversations")
def create_conversation(
    case_id: int,
    req: CreateConversationRequest = CreateConversationRequest(),
    db: Session = Depends(get_db),
):
    """创建对话会话（校验案件状态非 NEW）"""
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")

    # 仅允许已分析完成的案件创建对话
    if case.status == "NEW":
        raise HTTPException(status_code=400, detail="请先完成案件分析")

    conversation = Conversation(
        case_id=case_id,
        title=req.title,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return {
        "id": conversation.id,
        "case_id": conversation.case_id,
        "title": conversation.title,
        "created_at": str(conversation.created_at) if conversation.created_at else None,
    }


# ───────────── GET /api/cases/{case_id}/conversations ─────────────

@router.get("/cases/{case_id}/conversations")
def list_conversations(
    case_id: int,
    db: Session = Depends(get_db),
):
    """获取案件的对话列表（按创建时间倒序）"""
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")

    conversations = (
        db.query(Conversation)
        .filter(Conversation.case_id == case_id)
        .order_by(Conversation.created_at.desc())
        .all()
    )

    result = []
    for conv in conversations:
        msg_count = (
            db.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conv.id)
            .count()
        )
        result.append(ConversationResponse(
            id=conv.id,
            case_id=conv.case_id,
            title=conv.title,
            message_count=msg_count,
            created_at=str(conv.created_at) if conv.created_at else None,
            updated_at=str(conv.updated_at) if conv.updated_at else None,
        ))

    return result


# ───────────── GET /api/conversations/{conversation_id}/messages ─────────────

@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """获取对话的消息列表"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    messages = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.asc())
        .all()
    )

    return [
        MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            role=msg.role,
            content=msg.content,
            created_at=str(msg.created_at) if msg.created_at else None,
        )
        for msg in messages
    ]


# ───────────── POST /api/conversations/{conversation_id}/chat/stream ─────────────

def _build_case_context(db: Session, case_id: int) -> str:
    """构建案件上下文作为 system prompt 的一部分"""
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        return ""

    parts = []

    # Agent 分析输出
    if case.agent_output_json:
        try:
            agent_output = json.loads(case.agent_output_json)
            summary = agent_output.get("case_summary", "")
            risk_level = agent_output.get("risk_level", "")
            root_causes = agent_output.get("root_causes", [])
            recommendations = agent_output.get("recommendations", [])

            parts.append(f"## 案件分析总结\n风险等级: {risk_level}\n{summary}")

            if root_causes:
                causes_text = "\n".join([
                    f"- {rc.get('label', '')}: {rc.get('explanation', '')} (置信度: {rc.get('confidence', 0):.0%})"
                    for rc in root_causes
                ])
                parts.append(f"## 根因分析\n{causes_text}")

            if recommendations:
                recs_text = "\n".join([
                    f"- [{rec.get('action_type', '')}] {rec.get('title', '')}: {rec.get('why', '')}"
                    for rec in recommendations
                ])
                parts.append(f"## 动作建议\n{recs_text}")
        except Exception:
            pass

    # 证据摘要
    evidence_items = db.query(EvidenceItem).filter(EvidenceItem.case_id == case_id).all()
    if evidence_items:
        ev_text = "\n".join([
            f"- [EV-{101 + i}] [{ev.evidence_type}] {ev.summary or '无摘要'}"
            for i, ev in enumerate(evidence_items)
        ])
        parts.append(f"## 证据链\n{ev_text}")

    # 商家信息
    merchant = case.merchant
    if merchant:
        parts.append(
            f"## 商家信息\n名称: {merchant.name}\n行业: {merchant.industry}\n"
            f"店铺等级: {merchant.store_level}\n结算周期: {merchant.settlement_cycle_days}天"
        )

    return "\n\n".join(parts)


def _build_messages_for_llm(
    case_context: str,
    history_messages: list,
    user_message: str,
    max_rounds: int = 20,
) -> list[dict]:
    """构建 LLM 消息列表，包含 system prompt + 对话历史（滑动窗口）+ 用户最新消息"""
    system_prompt = (
        "你是一个专业的风控分析助手。以下是当前案件的分析上下文，请基于这些已有数据和分析结果回答用户的问题。"
        "如果问题超出已有数据范围，请如实回答'暂无相关数据'。不要编造不存在的数据。\n\n"
        f"{case_context}"
    )

    messages = [{"role": "system", "content": system_prompt}]

    # 滑动窗口：最多 20 轮（40 条消息）
    max_messages = max_rounds * 2
    recent_history = history_messages[-max_messages:] if len(history_messages) > max_messages else history_messages

    for msg in recent_history:
        messages.append({"role": msg.role, "content": msg.content})

    # 用户最新消息
    messages.append({"role": "user", "content": user_message})

    return messages


def _try_generate_title(
    db: Session,
    conversation_id: int,
    user_message: str,
    assistant_reply: str,
) -> None:
    """首轮对话完成后，用 LLM 生成简短对话标题（不超过 20 字）。
    仅在消息数 == 2（1 条 user + 1 条 assistant）时触发。
    失败时静默 fallback，不影响对话流程。
    """
    try:
        msg_count = (
            db.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conversation_id)
            .count()
        )
        if msg_count != 2:
            return  # 非首轮对话，跳过

        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv or conv.title != "新对话":
            return  # 标题已自定义，跳过

        if not is_llm_enabled():
            return

        # 用 LLM 生成标题
        title_prompt = (
            "根据以下对话内容，生成一个简短的中文标题（不超过15个字，不要加引号和标点）。\n\n"
            f"用户: {user_message[:200]}\n"
            f"助手: {assistant_reply[:500]}\n\n"
            "标题:"
        )
        title = chat_completion(
            messages=[{"role": "user", "content": title_prompt}],
            temperature=0.3,
            max_tokens=30,
        )
        title = title.strip().strip('"').strip("'").strip("《").strip("》")[:20]
        if title:
            conv.title = title
            db.commit()
            logger.info("对话 %d 自动生成标题: %s", conversation_id, title)

    except Exception as e:
        logger.warning("自动生成对话标题失败（不影响对话）: %s", e)


@router.post("/conversations/{conversation_id}/chat/stream")
async def chat_stream(
    conversation_id: int,
    req: ChatMessageRequest,
    db: Session = Depends(get_db),
):
    """SSE 流式对话接口"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    case_id = conversation.case_id

    # 持久化用户消息
    user_msg = ConversationMessage(
        conversation_id=conversation_id,
        role="user",
        content=req.message,
    )
    db.add(user_msg)
    db.commit()

    # 获取对话历史
    history_messages = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.asc())
        .all()
    )

    # 构建上下文
    case_context = _build_case_context(db, case_id)
    llm_messages = _build_messages_for_llm(
        case_context, history_messages[:-1], req.message  # 排除刚添加的用户消息（已在末尾）
    )

    # 使用 asyncio.Queue 在回调和流生成器之间传递事件
    event_queue: asyncio.Queue = asyncio.Queue()

    def _sync_chat():
        """在线程池中运行同步 LLM 调用"""
        start_time = _time.time()
        full_content = ""

        try:
            if not is_llm_enabled():
                # LLM 未启用时返回 mock 回复
                mock_reply = "当前 LLM 未启用，无法进行对话分析。请在配置中启用 LLM。"
                event_queue.put_nowait(("chat_chunk", {"content": mock_reply}))
                full_content = mock_reply
            else:
                def on_chunk(delta: str):
                    nonlocal full_content
                    full_content += delta
                    event_queue.put_nowait(("chat_chunk", {"content": delta}))

                chat_completion_stream(
                    messages=llm_messages,
                    on_chunk=on_chunk,
                    temperature=0.3,
                    max_tokens=2048,
                )

            elapsed_ms = int((_time.time() - start_time) * 1000)
            event_queue.put_nowait(("chat_done", {
                "content": full_content,
                "elapsed_ms": elapsed_ms,
            }))

            # 持久化 assistant 消息
            from app.core.database import SessionLocal
            thread_db = SessionLocal()
            try:
                assistant_msg = ConversationMessage(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_content,
                )
                thread_db.add(assistant_msg)
                thread_db.commit()

                # ── 首轮对话后自动生成标题 ──
                _try_generate_title(
                    thread_db, conversation_id,
                    req.message, full_content,
                )
            finally:
                thread_db.close()

        except Exception as e:
            logger.error("对话 LLM 调用失败: %s", e)
            event_queue.put_nowait(("chat_error", {"error": str(e)}))

    async def run_chat():
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _sync_chat)

    async def event_generator():
        chat_task = asyncio.create_task(run_chat())

        try:
            while True:
                try:
                    event_type, data = await asyncio.wait_for(
                        event_queue.get(), timeout=30.0
                    )
                    data_str = json.dumps(data, ensure_ascii=False)
                    yield f"event: {event_type}\ndata: {data_str}\n\n"

                    if event_type in ("chat_done", "chat_error"):
                        break
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            if not chat_task.done():
                chat_task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
