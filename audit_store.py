"""Persistence helpers for quality reviews and FAQ candidates."""

import json
import time

from sqlalchemy import desc, insert, select

from database import (
    conversations,
    faq_candidates,
    get_engine,
    init_db,
    quality_reviews,
    tool_calls,
)


def save_quality_review(
    *,
    account_id: str,
    content: str,
    keywords: str | None,
    result: str,
    structured_result: dict,
    conversation_id: str | None = None,
) -> int:
    init_db()
    with get_engine().begin() as conn:
        value = conn.execute(
            insert(quality_reviews).values(
                account_id=account_id,
                conversation_id=conversation_id,
                content=content,
                keywords=keywords or "",
                result=result,
                structured_result=json.dumps(
                    structured_result or {},
                    ensure_ascii=False,
                ),
                created_at=int(time.time()),
            )
        )
        return int(value.inserted_primary_key[0])


def save_faq_candidate(
    *,
    account_id: str,
    question: str,
    answer: str,
    score: int,
    status: str = "approved",
    conversation_id: str | None = None,
) -> int:
    init_db()
    with get_engine().begin() as conn:
        value = conn.execute(
            insert(faq_candidates).values(
                account_id=account_id,
                conversation_id=conversation_id,
                question=question,
                answer=answer,
                score=score,
                status=status,
                created_at=int(time.time()),
            )
        )
        return int(value.inserted_primary_key[0])


def list_tool_calls(
    conversation_id: str,
    account_id: str,
    limit: int = 100,
) -> list[dict]:
    init_db()
    with get_engine().connect() as conn:
        rows = conn.execute(
            select(tool_calls)
            .select_from(
                tool_calls.join(
                    conversations,
                    tool_calls.c.conversation_id == conversations.c.id,
                )
            )
            .where(tool_calls.c.conversation_id == conversation_id)
            .where(conversations.c.account_id == account_id)
            .order_by(desc(tool_calls.c.created_at), desc(tool_calls.c.id))
            .limit(limit)
        ).mappings().all()
    return [_decode_json_fields(dict(row), ("input_json", "output_json")) for row in rows]


def list_quality_reviews(
    account_id: str,
    conversation_id: str | None = None,
    limit: int = 50,
) -> list[dict]:
    init_db()
    query = select(quality_reviews).order_by(
        desc(quality_reviews.c.created_at),
        desc(quality_reviews.c.id),
    ).limit(limit)
    query = query.where(quality_reviews.c.account_id == account_id)
    if conversation_id:
        query = query.where(quality_reviews.c.conversation_id == conversation_id)
    with get_engine().connect() as conn:
        rows = conn.execute(query).mappings().all()
    return [_decode_json_fields(dict(row), ("structured_result",)) for row in rows]


def list_faq_candidates(
    account_id: str | None = None,
    limit: int = 50,
) -> list[dict]:
    init_db()
    query = select(faq_candidates).order_by(
        desc(faq_candidates.c.created_at),
        desc(faq_candidates.c.id),
    ).limit(limit)
    if account_id:
        query = query.where(faq_candidates.c.account_id == account_id)
    with get_engine().connect() as conn:
        rows = conn.execute(query).mappings().all()
    return [dict(row) for row in rows]


def _decode_json_fields(item: dict, fields: tuple[str, ...]) -> dict:
    for field in fields:
        try:
            item[field] = json.loads(item.get(field) or "{}")
        except json.JSONDecodeError:
            item[field] = {}
    return item
