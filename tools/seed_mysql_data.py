"""Seed MySQL with product, order, tracking, and FAQ demo data."""

from __future__ import annotations

import argparse
import time

from sqlalchemy import delete, insert

from database import faq_documents, get_engine, init_db, orders, products, tracking_events
from seed_data import (
    build_default_faq_rows,
    build_demo_order_rows,
    build_demo_tracking_rows,
    build_product_rows,
)


DEFAULT_ACCOUNT_ID = "100000"


def seed(database_url: str | None = None) -> dict[str, int]:
    init_db()
    engine = get_engine(database_url)
    now = int(time.time())
    counts: dict[str, int] = {}

    product_rows = build_product_rows()
    order_rows = build_demo_order_rows(DEFAULT_ACCOUNT_ID, now)
    tracking_rows = build_demo_tracking_rows("SF1000000001", now)
    faq_rows = build_default_faq_rows(DEFAULT_ACCOUNT_ID, now)

    with engine.begin() as conn:
        for table in (tracking_events, orders, products, faq_documents):
            conn.execute(delete(table))

        if product_rows:
            conn.execute(insert(products), product_rows)
        if order_rows:
            conn.execute(insert(orders), order_rows)
        if tracking_rows:
            conn.execute(insert(tracking_events), tracking_rows)
        if faq_rows:
            conn.execute(insert(faq_documents), faq_rows)

        counts["products"] = len(product_rows)
        counts["orders"] = len(order_rows)
        counts["tracking_events"] = len(tracking_rows)
        counts["faq_documents"] = len(faq_rows)

    engine.dispose()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=None, help="SQLAlchemy database URL")
    args = parser.parse_args()
    counts = seed(args.database_url)
    for table_name, count in counts.items():
        print(f"{table_name}: {count} rows seeded")


if __name__ == "__main__":
    main()
