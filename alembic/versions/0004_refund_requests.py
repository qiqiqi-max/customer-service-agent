"""add refund request approval state machine

Revision ID: 0004_refund_requests
Revises: 0003_conversation_foreign_keys
Create Date: 2026-09-02
"""

from alembic import op
from sqlalchemy import BigInteger, Column, ForeignKey, String, Table, Text


revision = "0004_refund_requests"
down_revision = "0003_conversation_foreign_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "refund_requests",
        Column("id", String(100), primary_key=True),
        Column("account_id", String(100), nullable=False),
        Column("order_id", String(100), ForeignKey("orders.order_id"), nullable=False),
        Column("reason", Text, nullable=False),
        Column("status", String(32), nullable=False),
        Column("created_at", BigInteger, nullable=False),
        Column("updated_at", BigInteger, nullable=False),
        Column("approved_at", BigInteger, nullable=True),
        Column("executed_at", BigInteger, nullable=True),
        Column("rejected_at", BigInteger, nullable=True),
        Column("failure_reason", Text, nullable=True),
    )
    op.create_index("ix_refund_requests_account_id", "refund_requests", ["account_id"])
    op.create_index("ix_refund_requests_order_id", "refund_requests", ["order_id"])
    op.create_index("ix_refund_requests_status", "refund_requests", ["status"])
    op.create_index("ix_refund_requests_updated_at", "refund_requests", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_refund_requests_updated_at", table_name="refund_requests")
    op.drop_index("ix_refund_requests_status", table_name="refund_requests")
    op.drop_index("ix_refund_requests_order_id", table_name="refund_requests")
    op.drop_index("ix_refund_requests_account_id", table_name="refund_requests")
    op.drop_table("refund_requests")
