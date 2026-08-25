"""MySQL-backed order and tracking access helpers."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from sqlalchemy import delete, insert, select, update

from database import get_engine, init_db, orders as orders_table, tracking_events
from config import language
from seed_data import build_demo_order_rows, build_demo_tracking_rows


class OrderStatus(str, Enum):
    SHIPPED = "已发货" if language == "zh" else "Shipped"
    PENDING = "未发货" if language == "zh" else "Not Shipped"
    REFUNDED = "已退款" if language == "zh" else "Refunded"


@dataclass
class Order:
    order_id: str
    status: OrderStatus
    product: str
    account_id: str
    tracking_number: Optional[str] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        data = {
            "order_id": self.order_id,
            "status": self.status.value,
            "product": self.product,
            "account_id": self.account_id,
        }
        if self.tracking_number is not None:
            data["tracking_number"] = self.tracking_number
        if self.reason is not None:
            data["reason"] = self.reason
        return data


async def get_order(account_id: str, order_id: str) -> Optional[Dict[str, str]]:
    init_db()
    await _ensure_account_seeded(account_id)
    with get_engine().connect() as conn:
        row = conn.execute(
            select(orders_table).where(orders_table.c.account_id == account_id).where(
                orders_table.c.order_id == order_id
            )
        ).mappings().first()
    return _row_to_order(row) if row else None


async def get_orders_by_product(account_id: str, product: str) -> List[Dict[str, str]]:
    init_db()
    await _ensure_account_seeded(account_id)
    with get_engine().connect() as conn:
        rows = conn.execute(
            select(orders_table)
            .where(orders_table.c.account_id == account_id)
            .where(orders_table.c.product_name == product)
            .order_by(orders_table.c.created_at.asc())
        ).mappings().all()
    return [_row_to_order(row) for row in rows]


async def get_all_orders(account_id: str) -> List[Dict[str, str]]:
    init_db()
    await _ensure_account_seeded(account_id)
    with get_engine().connect() as conn:
        rows = conn.execute(
            select(orders_table)
            .where(orders_table.c.account_id == account_id)
            .order_by(orders_table.c.created_at.asc())
        ).mappings().all()
    return [_row_to_order(row) for row in rows]


async def update_order_status(
    account_id: str, order_id: str, status: OrderStatus, reason: Optional[str] = None
) -> bool:
    init_db()
    await _ensure_account_seeded(account_id)
    now = int(time.time())
    with get_engine().begin() as conn:
        result = conn.execute(
            update(orders_table)
            .where(orders_table.c.account_id == account_id)
            .where(orders_table.c.order_id == order_id)
            .values(status=status.value, reason=reason, updated_at=now)
        )
    return result.rowcount > 0


def _row_to_order(row: dict) -> Dict[str, str]:
    data = dict(row)
    data["product"] = data.pop("product_name")
    return {k: str(v) for k, v in data.items() if v is not None}


async def _ensure_account_seeded(account_id: str) -> None:
    with get_engine().connect() as conn:
        existing = conn.execute(
            select(orders_table.c.order_id).where(orders_table.c.account_id == account_id)
        ).first()
    if existing:
        return

    now = int(time.time())
    order_rows = build_demo_order_rows(account_id, now)
    tracking_rows = []
    for order in order_rows:
        if order.get("tracking_number"):
            tracking_rows.extend(
                build_demo_tracking_rows(str(order["tracking_number"]), now)
            )
            break

    with get_engine().begin() as conn:
        conn.execute(insert(orders_table), order_rows)
        if tracking_rows:
            conn.execute(insert(tracking_events), tracking_rows)
