"""record who approved, rejected or executed a refund request

Revision ID: 0005_refund_actors
Revises: 0004_refund_requests
Create Date: 2026-09-09
"""

from alembic import op
from sqlalchemy import Column, String, inspect


revision = "0005_refund_actors"
down_revision = "0004_refund_requests"
branch_labels = None
depends_on = None

ACTOR_COLUMNS = ("approved_by", "rejected_by", "executed_by")


def _existing_columns() -> set[str]:
    return {
        column["name"]
        for column in inspect(op.get_bind()).get_columns("refund_requests")
    }


def upgrade() -> None:
    existing = _existing_columns()
    missing = [name for name in ACTOR_COLUMNS if name not in existing]
    if not missing:
        return
    with op.batch_alter_table("refund_requests") as batch:
        for name in missing:
            batch.add_column(Column(name, String(100), nullable=True))


def downgrade() -> None:
    existing = _existing_columns()
    present = [name for name in ACTOR_COLUMNS if name in existing]
    if not present:
        return
    with op.batch_alter_table("refund_requests") as batch:
        for name in present:
            batch.drop_column(name)
