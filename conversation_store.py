import json
import time
from typing import Any
from uuid import uuid4

from sqlalchemy import case, desc, insert, select, update

import config
from arkitect.types.llm.model import ArkChatRequest, ArkChatResponse
from database import conversations, get_engine, init_db, messages, tool_calls


class ConversationAccessError(Exception):
    pass


def ensure_conversation(
    conversation_id: str | None,
    account_id: str,
    title: str | None = None,
) -> str:
    init_db()
    resolved_id = conversation_id or f"conv_{uuid4().hex}"
    now = _now()
    with get_engine().begin() as conn:
        existing = conn.execute(
            select(conversations.c.id, conversations.c.account_id).where(
                conversations.c.id == resolved_id
            )
        ).mappings().first()
        if existing:
            if existing["account_id"] != account_id:
                raise ConversationAccessError(
                    f"Conversation {resolved_id} does not belong to account {account_id}."
                )
            conn.execute(
                update(conversations)
                .where(conversations.c.id == resolved_id)
                .values(updated_at=now)
            )
        else:
            conn.execute(
                insert(conversations).values(
                    id=resolved_id,
                    account_id=account_id,
                    title=title or "新会话",
                    created_at=now,
                    updated_at=now,
                )
            )
    return resolved_id


def record_chat_turn(
    conversation_id: str,
    request: ArkChatRequest,
    response: ArkChatResponse,
) -> None:
    init_db()
    user_message = _latest_message(request, "user")
    assistant_text = _assistant_text(response)
    bot_usage = (
        response.bot_usage.model_dump(mode="json") if response.bot_usage else None
    )
    with get_engine().begin() as conn:
        if user_message:
            _insert_message(
                conn,
                conversation_id,
                "user",
                user_message,
                {"source": "chat_request"},
            )
        if assistant_text:
            _insert_message(
                conn,
                conversation_id,
                "assistant",
                assistant_text,
                {
                    "source": "chat_response",
                    "model": response.model,
                    "bot_usage": bot_usage,
                },
            )
        _insert_tool_calls(conn, conversation_id, bot_usage)
        conn.execute(
            update(conversations)
            .where(conversations.c.id == conversation_id)
            .values(
                title=case(
                    (
                        conversations.c.title == "新会话",
                        _make_title(user_message or assistant_text),
                    ),
                    else_=conversations.c.title,
                ),
                updated_at=_now(),
            )
        )


def attach_conversation_metadata(
    response: ArkChatResponse,
    conversation_id: str,
) -> ArkChatResponse:
    metadata = response.metadata or {}
    metadata["conversation_id"] = conversation_id
    response.metadata = metadata
    return response


def list_conversations(limit: int = 50, account_id: str | None = None) -> dict:
    init_db()
    last_message = (
        select(messages.c.content)
        .where(messages.c.conversation_id == conversations.c.id)
        .order_by(messages.c.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    query = (
        select(
            conversations.c.id,
            conversations.c.account_id,
            conversations.c.title,
            conversations.c.created_at,
            conversations.c.updated_at,
            last_message.label("last_message"),
        )
        .order_by(desc(conversations.c.updated_at))
        .limit(limit)
    )
    if account_id:
        query = query.where(conversations.c.account_id == account_id)

    with get_engine().connect() as conn:
        rows = conn.execute(query).mappings().all()
    return {"conversations": [dict(row) for row in rows], "total": len(rows)}


def get_conversation(
    conversation_id: str,
    account_id: str | None = None,
) -> dict | None:
    init_db()
    query = select(
        conversations.c.id,
        conversations.c.account_id,
        conversations.c.title,
        conversations.c.created_at,
        conversations.c.updated_at,
    ).where(conversations.c.id == conversation_id)
    if account_id:
        query = query.where(conversations.c.account_id == account_id)

    with get_engine().connect() as conn:
        conversation = conn.execute(query).mappings().first()
        if not conversation:
            return None
        message_rows = conn.execute(
            select(
                messages.c.id,
                messages.c.role,
                messages.c.content,
                messages.c.metadata,
                messages.c.created_at,
            )
            .where(messages.c.conversation_id == conversation_id)
            .order_by(messages.c.id.asc())
        ).mappings().all()

    return {
        **dict(conversation),
        "messages": [_message_row_to_dict(row) for row in message_rows],
    }


def _insert_message(
    conn,
    conversation_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any],
) -> None:
    conn.execute(
        insert(messages).values(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata=json.dumps(metadata or {}, ensure_ascii=False),
            created_at=_now(),
        )
    )


def _insert_tool_calls(conn, conversation_id: str, bot_usage: dict | None) -> None:
    for action in (bot_usage or {}).get("action_details") or []:
        for detail in action.get("tool_details") or []:
            conn.execute(
                insert(tool_calls).values(
                    conversation_id=conversation_id,
                    tool_name=detail.get("name") or action.get("name") or "tool",
                    input_json=json.dumps(detail.get("input"), ensure_ascii=False),
                    output_json=json.dumps(detail.get("output"), ensure_ascii=False),
                    created_at=_now(),
                )
            )


def _latest_message(request: ArkChatRequest, role: str) -> str:
    for message in reversed(request.messages):
        if message.role == role and message.content:
            return str(message.content)
    return ""


def _assistant_text(response: ArkChatResponse) -> str:
    if not response.choices:
        return ""
    return response.choices[0].message.content or ""


def _make_title(text: str) -> str:
    value = (text or "新会话").strip().replace("\n", " ")
    return value[:30] or "新会话"


def _now() -> int:
    return int(time.time())


def _message_row_to_dict(row) -> dict:
    data = dict(row)
    try:
        data["metadata"] = json.loads(data.get("metadata") or "{}")
    except json.JSONDecodeError:
        data["metadata"] = {}
    return data
