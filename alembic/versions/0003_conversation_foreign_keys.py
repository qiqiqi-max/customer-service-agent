"""add conversation foreign keys

Revision ID: 0003_conversation_foreign_keys
Revises: 0002_quality_review_account
Create Date: 2026-08-26
"""

from alembic import op


revision = "0003_conversation_foreign_keys"
down_revision = "0002_quality_review_account"
branch_labels = None
depends_on = None


def upgrade() -> None:
    _create_fk(
        "messages",
        "fk_messages_conversation_id_conversations",
        ondelete="CASCADE",
    )
    _create_fk(
        "tool_calls",
        "fk_tool_calls_conversation_id_conversations",
        ondelete="CASCADE",
    )
    _create_fk(
        "quality_reviews",
        "fk_quality_reviews_conversation_id_conversations",
        ondelete="SET NULL",
    )
    _create_fk(
        "faq_candidates",
        "fk_faq_candidates_conversation_id_conversations",
        ondelete="SET NULL",
    )


def downgrade() -> None:
    _drop_fk("faq_candidates", "fk_faq_candidates_conversation_id_conversations")
    _drop_fk("quality_reviews", "fk_quality_reviews_conversation_id_conversations")
    _drop_fk("tool_calls", "fk_tool_calls_conversation_id_conversations")
    _drop_fk("messages", "fk_messages_conversation_id_conversations")


def _create_fk(table_name: str, constraint_name: str, ondelete: str) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.create_foreign_key(
            constraint_name,
            "conversations",
            ["conversation_id"],
            ["id"],
            ondelete=ondelete,
        )


def _drop_fk(table_name: str, constraint_name: str) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_constraint(constraint_name, type_="foreignkey")
