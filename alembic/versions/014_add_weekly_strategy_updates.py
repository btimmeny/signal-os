"""Add weekly_strategy_updates table for Friday execution updates.

Revision ID: 014
"""

from alembic import op
import sqlalchemy as sa


revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weekly_strategy_updates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("week_start_date", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Enum("DRAFT", "SENT", name="update_status"), nullable=False, server_default="DRAFT"),
        sa.Column("narrative_options", sa.Text(), nullable=True),
        sa.Column("recommended_narrative", sa.Integer(), nullable=True),
        sa.Column("confidence_score", sa.Integer(), nullable=True),
        sa.Column("confidence_trend", sa.String(32), nullable=True),
        sa.Column("confidence_explanation", sa.Text(), nullable=True),
        sa.Column("score_components", sa.Text(), nullable=True),
        sa.Column("narrative_continuity", sa.Text(), nullable=True),
        sa.Column("forwardable_body", sa.Text(), nullable=True),
        sa.Column("signal_snapshot", sa.Text(), nullable=True),
        sa.Column("previous_update_id", sa.Uuid(), sa.ForeignKey("weekly_strategy_updates.id", ondelete="SET NULL"), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("weekly_strategy_updates")
