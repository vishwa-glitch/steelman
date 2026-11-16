"""Add in-flight claims on debates, and per-visitor start counts.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("debates", sa.Column("ai_turn_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("debates", sa.Column("judge_started_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "visitor_usage",
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("client_hash", sa.String(64), primary_key=True),
        sa.Column("starts", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("visitor_usage")
    op.drop_column("debates", "judge_started_at")
    op.drop_column("debates", "ai_turn_started_at")
