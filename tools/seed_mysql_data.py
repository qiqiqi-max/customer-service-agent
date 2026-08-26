"""Seed MySQL with product, order, tracking, and FAQ starter data."""

from __future__ import annotations

import argparse
import time

from sqlalchemy import delete, func, insert, select

from database import (
    faq_documents,
    get_engine,
    metadata,
    migrate_database,
    orders,
    products,
    tracking_events,
)
from seed_data import (
    build_default_faq_rows,
    build_demo_order_rows,
    build_demo_tracking_rows,
    build_product_rows,
    ensure_seed_data,
)


DEFAULT_ACCOUNT_ID = "100000"


def seed(database_url: str | None = None, reset: bool = False) -> dict[str, int]:
    if database_url is None:
        migrate_database()

    engine = get_engine(database_url)
    if database_url is not None:
        metadata.create_all(engine)

    if not reset:
        before = _table_counts(engine)
        ensure_seed_data(engine)
        after = _table_counts(engine)
        return {
            table_name: after[table_name] - before[table_name]
            for table_name in before
        }

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


def _table_counts(engine) -> dict[str, int]:
    tables = {
        "products": products,
        "orders": orders,
        "tracking_events": tracking_events,
        "faq_documents": faq_documents,
    }
    with engine.connect() as conn:
        return {
            table_name: conn.execute(select(func.count()).select_from(table)).scalar_one()
            for table_name, table in tables.items()
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=None, help="SQLAlchemy database URL")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear and recreate starter product/order/tracking/FAQ rows.",
    )
    args = parser.parse_args()
    counts = seed(args.database_url, reset=args.reset)
    for table_name, count in counts.items():
        action = "reset" if args.reset else "inserted"
        print(f"{table_name}: {count} rows {action}")


if __name__ == "__main__":
    main()
