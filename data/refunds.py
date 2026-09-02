"""Refund request state machine backed by MySQL or SQLite."""

from __future__ import annotations

import time
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import insert, select, update

from database import get_engine, init_db, orders, refund_requests
from data.orders import OrderStatus


class RefundError(ValueError):
    """Raised when a refund transition is invalid."""


class RefundStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    EXECUTED = "executed"
    REJECTED = "rejected"
    FAILED = "failed"


ACTIVE_STATUSES = {
    RefundStatus.PENDING_APPROVAL.value,
    RefundStatus.APPROVED.value,
}


def _now() -> int:
    return int(time.time())


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row) if row else {}


def _get_request(conn, refund_id: str, account_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        select(refund_requests).where(
            refund_requests.c.id == refund_id,
            refund_requests.c.account_id == account_id,
        )
    ).mappings().first()
    return _row_to_dict(row) if row else None


async def create_refund_request(
    account_id: str,
    order_id: str,
    reason: str = "",
) -> dict[str, Any]:
    init_db()
    now = _now()
    with get_engine().begin() as conn:
        order = conn.execute(
            select(orders)
            .where(
                orders.c.account_id == account_id,
                orders.c.order_id == order_id,
            )
            .with_for_update()
        ).mappings().first()
        if not order:
            raise RefundError("Order does not exist")
        if order["status"] == OrderStatus.REFUNDED.value:
            raise RefundError("Order has already been refunded, cannot refund again")

        existing = conn.execute(
            select(refund_requests)
            .where(
                refund_requests.c.account_id == account_id,
                refund_requests.c.order_id == order_id,
                refund_requests.c.status.in_(ACTIVE_STATUSES),
            )
            .order_by(refund_requests.c.created_at.desc())
            .limit(1)
        ).mappings().first()
        if existing:
            result = _row_to_dict(existing)
            result["message"] = "Refund request already awaits approval"
            return result

        refund_id = f"refund_{uuid4().hex}"
        conn.execute(
            insert(refund_requests).values(
                id=refund_id,
                account_id=account_id,
                order_id=order_id,
                reason=reason,
                status=RefundStatus.PENDING_APPROVAL.value,
                created_at=now,
                updated_at=now,
            )
        )
        result = _get_request(conn, refund_id, account_id) or {}
        result["message"] = "Refund request submitted and awaits manual approval"
        return result


async def approve_refund(account_id: str, refund_id: str) -> dict[str, Any]:
    return await _transition_refund(
        account_id,
        refund_id,
        RefundStatus.PENDING_APPROVAL.value,
        RefundStatus.APPROVED.value,
        approved_at=_now(),
    )


async def reject_refund(account_id: str, refund_id: str) -> dict[str, Any]:
    return await _transition_refund(
        account_id,
        refund_id,
        RefundStatus.PENDING_APPROVAL.value,
        RefundStatus.REJECTED.value,
        rejected_at=_now(),
    )


async def execute_refund(account_id: str, refund_id: str) -> dict[str, Any]:
    init_db()
    now = _now()
    try:
        with get_engine().begin() as conn:
            request_row = conn.execute(
                select(refund_requests)
                .where(
                    refund_requests.c.id == refund_id,
                    refund_requests.c.account_id == account_id,
                )
                .with_for_update()
            ).mappings().first()
            request = _row_to_dict(request_row) if request_row else None
            if not request:
                raise RefundError("Refund request does not exist")
            if request["status"] != RefundStatus.APPROVED.value:
                raise RefundError("Refund must be approved before execution")

            order = conn.execute(
                select(orders)
                .where(
                    orders.c.account_id == account_id,
                    orders.c.order_id == request["order_id"],
                )
                .with_for_update()
            ).mappings().first()
            if not order:
                raise RefundError("Order does not exist")
            if order["status"] == OrderStatus.REFUNDED.value:
                raise RefundError("Order has already been refunded, cannot refund again")

            conn.execute(
                update(orders)
                .where(
                    orders.c.account_id == account_id,
                    orders.c.order_id == request["order_id"],
                )
                .values(
                    status=OrderStatus.REFUNDED.value,
                    reason=request["reason"],
                    updated_at=now,
                )
            )
            conn.execute(
                update(refund_requests)
                .where(
                    refund_requests.c.id == refund_id,
                    refund_requests.c.account_id == account_id,
                    refund_requests.c.status == RefundStatus.APPROVED.value,
                )
                .values(
                    status=RefundStatus.EXECUTED.value,
                    updated_at=now,
                    executed_at=now,
                    failure_reason=None,
                )
            )
            result = _get_request(conn, refund_id, account_id) or {}
            result["message"] = "Refund executed successfully"
            return result
    except RefundError:
        raise
    except Exception as exc:
        with get_engine().begin() as conn:
            conn.execute(
                update(refund_requests)
                .where(
                    refund_requests.c.id == refund_id,
                    refund_requests.c.account_id == account_id,
                    refund_requests.c.status == RefundStatus.APPROVED.value,
                )
                .values(
                    status=RefundStatus.FAILED.value,
                    updated_at=_now(),
                    failure_reason=str(exc),
                )
            )
        raise RefundError(f"Refund execution failed: {exc}") from exc


async def get_refund_request(account_id: str, refund_id: str) -> dict[str, Any] | None:
    init_db()
    with get_engine().connect() as conn:
        return _get_request(conn, refund_id, account_id)


async def _transition_refund(
    account_id: str,
    refund_id: str,
    from_status: str,
    to_status: str,
    **timestamps: int,
) -> dict[str, Any]:
    init_db()
    now = _now()
    with get_engine().begin() as conn:
        request = _get_request(conn, refund_id, account_id)
        if not request:
            raise RefundError("Refund request does not exist")
        if request["status"] != from_status:
            raise RefundError(
                f"Refund request must be {from_status} before it can become {to_status}"
            )
        conn.execute(
            update(refund_requests)
            .where(
                refund_requests.c.id == refund_id,
                refund_requests.c.account_id == account_id,
                refund_requests.c.status == from_status,
            )
            .values(status=to_status, updated_at=now, **timestamps)
        )
        result = _get_request(conn, refund_id, account_id) or {}
        result["message"] = f"Refund request is now {to_status}"
        return result
