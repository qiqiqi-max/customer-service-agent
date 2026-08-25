"""create customer service persistence tables

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-25
"""

from alembic import op

from database import metadata


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    metadata.create_all(op.get_bind())


def downgrade() -> None:
    metadata.drop_all(op.get_bind())
