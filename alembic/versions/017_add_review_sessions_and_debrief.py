"""Add weekly review sessions and strategy debrief tables.

Feature 022 extension: ChatGPT Review Sessions and Strategy Debrief.

New tables:
- weekly_review_sessions
- strategy_debrief_records

Revision ID: 017
"""

from alembic import op
import sqlalchemy as sa


revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Weekly Review Sessions
    op.create_table(
        "weekly_review_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("week_date", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("session_title", sa.String(512), nullable=False),
        sa.Column("chatgpt_session_link", sa.String(2048), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Strategy Debrief Records
    op.create_table(
        "strategy_debrief_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("week_date", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("derived_insight", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("strategy_debrief_records")
    op.drop_table("weekly_review_sessions")
