"""MySQL-backed product catalog access."""

from __future__ import annotations

from sqlalchemy import select

from config import language
from database import get_engine, init_db, products as products_table


def get_products():
    init_db()
    with get_engine().connect() as conn:
        rows = conn.execute(
            select(products_table)
            .where(products_table.c.language == language)
            .order_by(products_table.c.id.asc())
        ).mappings().all()
    return {
        row["name"]: {
            "name": row["name"],
            "description": row["description"],
            "cover_image": row["cover_image"],
        }
        for row in rows
    }
