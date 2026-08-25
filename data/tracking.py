"""MySQL-backed shipping tracking access helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from sqlalchemy import select

from config import language
from database import get_engine, init_db, tracking_events


def get_tracking_info(tracking_number: str) -> Dict:
    init_db()
    with get_engine().connect() as conn:
        rows = conn.execute(
            select(tracking_events)
            .where(tracking_events.c.tracking_number == tracking_number)
            .order_by(tracking_events.c.event_time.asc())
        ).mappings().all()

    if not rows:
        return {
            "tracking_number": tracking_number,
            "current_status": "未知" if language == "zh" else "Unknown",
            "events": [],
        }

    events = [_row_to_event(row) for row in rows]
    return {
        "tracking_number": tracking_number,
        "current_status": events[-1]["status"],
        "events": events,
    }


def _row_to_event(row: dict) -> Dict[str, str]:
    data = dict(row)
    event_time = data.get("event_time") or 0
    data["time"] = datetime.fromtimestamp(int(event_time)).strftime("%Y-%m-%d %H:%M:%S")
    data.pop("event_time", None)
    data.pop("id", None)
    data.pop("created_at", None)
    return {k: str(v) for k, v in data.items() if v is not None}
