"""Create debates and usage tables.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "debates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("slug", sa.String(32), nullable=False),
        sa.Column("motion", sa.String(200), nullable=False),
        sa.Column("user_side", sa.String(3), nullable=False),
        sa.Column("difficulty", sa.String(10), nullable=False),
        sa.Column("turns", sa.JSON(), nullable=False),
        sa.Column("scorecard", sa.JSON(), nullable=True),
        sa.Column("judge_meta", sa.JSON(), nullable=True),
        sa.Column("client_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_debates_slug", "debates", ["slug"], unique=True)
    op.create_index("ix_debates_client_hash", "debates", ["client_hash"])
    op.create_index("ix_debates_created_at", "debates", ["created_at"])
    op.create_table(
        "usage",
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("ai_calls", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("usage")
    op.drop_table("debates")
