"""Database engine and schema shared by SQLite and MySQL deployments."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import (
    BigInteger,
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    event,
)
from sqlalchemy.pool import NullPool
from sqlalchemy.engine import Engine

import config
from seed_data import ensure_seed_data


metadata = MetaData()

products = Table(
    "products",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("language", String(16), nullable=False, index=True),
    Column("name", String(255), nullable=False, index=True),
    Column("description", Text, nullable=False),
    Column("cover_image", Text, nullable=False),
)

orders = Table(
    "orders",
    metadata,
    Column("order_id", String(100), primary_key=True),
    Column("account_id", String(100), nullable=False, index=True),
    Column("status", String(32), nullable=False, index=True),
    Column("product_name", String(255), nullable=False, index=True),
    Column("tracking_number", String(100), nullable=True, index=True),
    Column("reason", Text, nullable=True),
    Column("created_at", BigInteger, nullable=False),
    Column("updated_at", BigInteger, nullable=False, index=True),
)

refund_requests = Table(
    "refund_requests",
    metadata,
    Column("id", String(100), primary_key=True),
    Column("account_id", String(100), nullable=False, index=True),
    Column(
        "order_id",
        String(100),
        ForeignKey("orders.order_id"),
        nullable=False,
        index=True,
    ),
    Column("reason", Text, nullable=False),
    Column("status", String(32), nullable=False, index=True),
    Column("created_at", BigInteger, nullable=False),
    Column("updated_at", BigInteger, nullable=False, index=True),
    Column("approved_at", BigInteger, nullable=True),
    Column("executed_at", BigInteger, nullable=True),
    Column("rejected_at", BigInteger, nullable=True),
    Column("failure_reason", Text, nullable=True),
)

tracking_events = Table(
    "tracking_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("tracking_number", String(100), nullable=False, index=True),
    Column("event_time", BigInteger, nullable=False, index=True),
    Column("status", String(64), nullable=False),
    Column("location", String(255), nullable=False),
    Column("description", Text, nullable=False),
    Column("created_at", BigInteger, nullable=False),
)

faq_documents = Table(
    "faq_documents",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("account_id", String(100), nullable=False, index=True),
    Column("question", Text, nullable=False),
    Column("answer", Text, nullable=False),
    Column("score", Integer, nullable=False),
    Column("status", String(32), nullable=False, index=True),
    Column("source", String(32), nullable=False, index=True),
    Column("created_at", BigInteger, nullable=False),
)

conversations = Table(
    "conversations",
    metadata,
    Column("id", String(100), primary_key=True),
    Column("account_id", String(100), nullable=False, index=True),
    Column("title", String(255), nullable=False),
    Column("created_at", BigInteger, nullable=False),
    Column("updated_at", BigInteger, nullable=False, index=True),
)

messages = Table(
    "messages",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "conversation_id",
        String(100),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("role", String(32), nullable=False),
    Column("content", Text, nullable=False),
    Column("metadata", Text, nullable=False),
    Column("created_at", BigInteger, nullable=False),
)

tool_calls = Table(
    "tool_calls",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "conversation_id",
        String(100),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("tool_name", String(100), nullable=False),
    Column("input_json", Text, nullable=False),
    Column("output_json", Text, nullable=False),
    Column("created_at", BigInteger, nullable=False),
)

quality_reviews = Table(
    "quality_reviews",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("account_id", String(100), nullable=False, index=True),
    Column(
        "conversation_id",
        String(100),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    ),
    Column("content", Text, nullable=False),
    Column("keywords", Text, nullable=False),
    Column("result", Text, nullable=False),
    Column("structured_result", Text, nullable=False),
    Column("created_at", BigInteger, nullable=False),
)

faq_candidates = Table(
    "faq_candidates",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("account_id", String(100), nullable=False, index=True),
    Column(
        "conversation_id",
        String(100),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    ),
    Column("question", Text, nullable=False),
    Column("answer", Text, nullable=False),
    Column("score", Integer, nullable=False),
    Column("status", String(32), nullable=False, index=True),
    Column("created_at", BigInteger, nullable=False),
)


def get_database_url() -> str:
    configured = getattr(config, "database_url", "").strip()
    if configured:
        return configured

    path = Path(config.conversation_db_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.as_posix()}"


def is_sqlite() -> bool:
    return get_database_url().startswith("sqlite")


def get_engine(database_url: str | None = None) -> Engine:
    return _get_engine_for_url(database_url or get_database_url())


@lru_cache(maxsize=8)
def _get_engine_for_url(url: str) -> Engine:
    connect_args: dict[str, Any] = {}
    engine_options: dict[str, Any] = {
        "pool_pre_ping": True,
        "future": True,
    }
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        engine_options["poolclass"] = NullPool
    else:
        engine_options.update(pool_recycle=1800, pool_size=5, max_overflow=10)

    engine = create_engine(url, connect_args=connect_args, **engine_options)
    if url.startswith("sqlite"):
        _enable_sqlite_foreign_keys(engine)
    return engine


def init_db() -> None:
    engine = get_engine()
    metadata.create_all(engine)
    ensure_seed_data(engine)


def migrate_database() -> None:
    alembic_config = AlembicConfig(str(Path(__file__).resolve().parent / "alembic.ini"))
    command.upgrade(alembic_config, "head")


def dispose_engines() -> None:
    _get_engine_for_url.cache_clear()


def _enable_sqlite_foreign_keys(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
