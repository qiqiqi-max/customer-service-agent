import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

import config
from arkitect.types.llm.model import ArkChatRequest, ArkChatResponse


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
    with _connect() as conn:
        existing = conn.execute(
            "select id, account_id from conversations where id = ?",
            (resolved_id,),
        ).fetchone()
        if existing:
            if existing["account_id"] != account_id:
                raise ConversationAccessError(
                    f"Conversation {resolved_id} does not belong to account {account_id}."
                )
            conn.execute(
                "update conversations set updated_at = ? where id = ?",
                (now, resolved_id),
            )
        else:
            conn.execute(
                """
                insert into conversations(id, account_id, title, created_at, updated_at)
                values(?, ?, ?, ?, ?)
                """,
                (resolved_id, account_id, title or "新会话", now, now),
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

    with _connect() as conn:
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
        conn.execute(
            "update conversations set title = coalesce(nullif(title, '新会话'), ?), updated_at = ? where id = ?",
            (_make_title(user_message or assistant_text), _now(), conversation_id),
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
    with _connect() as conn:
        params: tuple = (limit,)
        account_filter = ""
        if account_id:
            account_filter = "where c.account_id = ?"
            params = (account_id, limit)
        rows = conn.execute(
            f"""
            select c.id, c.account_id, c.title, c.created_at, c.updated_at,
                   (
                     select content from messages m
                     where m.conversation_id = c.id
                     order by m.id desc
                     limit 1
                   ) as last_message
            from conversations c
            {account_filter}
            order by c.updated_at desc
            limit ?
            """,
            params,
        ).fetchall()
    return {"conversations": [_row_to_dict(row) for row in rows], "total": len(rows)}


def get_conversation(conversation_id: str, account_id: str | None = None) -> dict | None:
    init_db()
    with _connect() as conn:
        params = (conversation_id,)
        account_filter = ""
        if account_id:
            account_filter = "and account_id = ?"
            params = (conversation_id, account_id)
        conversation = conn.execute(
            f"""
            select id, account_id, title, created_at, updated_at
            from conversations
            where id = ? {account_filter}
            """,
            params,
        ).fetchone()
        if not conversation:
            return None
        messages = conn.execute(
            """
            select id, role, content, metadata, created_at
            from messages
            where conversation_id = ?
            order by id asc
            """,
            (conversation_id,),
        ).fetchall()
    return {
        **_row_to_dict(conversation),
        "messages": [_message_row_to_dict(row) for row in messages],
    }


def init_db() -> None:
    db_path = Path(config.conversation_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.execute(
            """
            create table if not exists conversations(
                id text primary key,
                account_id text not null,
                title text not null,
                created_at integer not null,
                updated_at integer not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists messages(
                id integer primary key autoincrement,
                conversation_id text not null,
                role text not null,
                content text not null,
                metadata text,
                created_at integer not null,
                foreign key(conversation_id) references conversations(id)
            )
            """
        )
        conn.execute(
            "create index if not exists idx_messages_conversation_id on messages(conversation_id)"
        )


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(config.conversation_db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _insert_message(
    conn: sqlite3.Connection,
    conversation_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        insert into messages(conversation_id, role, content, metadata, created_at)
        values(?, ?, ?, ?, ?)
        """,
        (
            conversation_id,
            role,
            content,
            json.dumps(metadata or {}, ensure_ascii=False),
            _now(),
        ),
    )


def _latest_message(request: ArkChatRequest, role: str) -> str:
    for message in reversed(request.messages):
        if message.role == role and message.content:
            return str(message.content)
    return ""


def _assistant_text(response: ArkChatResponse) -> str:
    if not response.choices:
        return ""
    message = response.choices[0].message
    return message.content or ""


def _make_title(text: str) -> str:
    value = (text or "新会话").strip().replace("\n", " ")
    return value[:30] or "新会话"


def _now() -> int:
    return int(time.time())


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {key: row[key] for key in row.keys()}


def _message_row_to_dict(row: sqlite3.Row) -> dict:
    data = _row_to_dict(row)
    try:
        data["metadata"] = json.loads(data.get("metadata") or "{}")
    except json.JSONDecodeError:
        data["metadata"] = {}
    return data
