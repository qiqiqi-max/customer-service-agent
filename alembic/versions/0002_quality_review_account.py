"""add account scope to quality reviews

Revision ID: 0002_quality_review_account
Revises: 0001_initial_schema
Create Date: 2026-08-25
"""

from alembic import op
from sqlalchemy import Column, String, inspect, text


revision = "0002_quality_review_account"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {
        column["name"]
        for column in inspect(bind).get_columns("quality_reviews")
    }
    if "account_id" in columns:
        return

    op.add_column(
        "quality_reviews",
        Column("account_id", String(100), nullable=True),
    )
    op.execute(
        text(
            "UPDATE quality_reviews "
            "SET account_id = '100000' "
            "WHERE account_id IS NULL"
        )
    )
    op.create_index(
        "ix_quality_reviews_account_id",
        "quality_reviews",
        ["account_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {
        column["name"]
        for column in inspect(bind).get_columns("quality_reviews")
    }
    if "account_id" not in columns:
        return
    op.drop_index("ix_quality_reviews_account_id", table_name="quality_reviews")
    op.drop_column("quality_reviews", "account_id")
