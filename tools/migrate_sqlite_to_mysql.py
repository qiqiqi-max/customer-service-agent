"""Copy persistence data from an existing SQLite database to MySQL.

Usage:
  python tools/migrate_sqlite_to_mysql.py ^
    --source sqlite:///D:/path/conversations.sqlite3 ^
    --target mysql+pymysql://user:password@localhost:3306/customer_service
"""

from __future__ import annotations

import argparse

from sqlalchemy import create_engine, insert, inspect, select

from database import (
    conversations,
    faq_candidates,
    messages,
    metadata,
    quality_reviews,
    tool_calls,
)


TABLES = (
    conversations,
    messages,
    tool_calls,
    quality_reviews,
    faq_candidates,
)


def migrate(source_url: str, target_url: str) -> dict[str, int]:
    source = create_engine(source_url, future=True)
    target = create_engine(target_url, future=True, pool_pre_ping=True)
    metadata.create_all(target)
    counts: dict[str, int] = {}

    with source.connect() as source_conn, target.begin() as target_conn:
        source_tables = set(inspect(source_conn).get_table_names())
        for table in TABLES:
            if table.name not in source_tables:
                counts[table.name] = 0
                continue

            source_columns = {
                column["name"]
                for column in inspect(source_conn).get_columns(table.name)
            }
            selected_columns = [
                column for column in table.c if column.name in source_columns
            ]
            rows = [
                dict(row)
                for row in source_conn.execute(select(*selected_columns)).mappings()
            ]
            if table.name == "quality_reviews":
                for row in rows:
                    row.setdefault("account_id", "100000")
            if rows:
                target_conn.execute(insert(table), rows)
            counts[table.name] = len(rows)

    source.dispose()
    target.dispose()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="SQLite SQLAlchemy URL")
    parser.add_argument("--target", required=True, help="MySQL SQLAlchemy URL")
    args = parser.parse_args()

    counts = migrate(args.source, args.target)
    for table_name, count in counts.items():
        print(f"{table_name}: {count} rows copied")


if __name__ == "__main__":
    main()
