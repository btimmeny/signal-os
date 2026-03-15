"""Add platform_leads and leadership_memos tables.

Revision ID: 012
"""

from alembic import op
import sqlalchemy as sa


revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_leads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False, index=True),
        sa.Column("role", sa.String(512), nullable=False),
        sa.Column("focus_area", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("initiative_ids", sa.Text(), nullable=True),
        sa.Column("active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "leadership_memos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("week_start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("author", sa.String(256), nullable=True),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "FINALIZED", "SENT", name="memo_status"),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("strategic_objective", sa.Text(), nullable=True),
        sa.Column("current_priorities", sa.Text(), nullable=True),
        sa.Column("progress_summary", sa.Text(), nullable=True),
        sa.Column("focus_next_week", sa.Text(), nullable=True),
        sa.Column("success_criteria", sa.Text(), nullable=True),
        sa.Column("lead_updates", sa.Text(), nullable=True),
        sa.Column("dashboard_snapshot", sa.Text(), nullable=True),
        sa.Column("audience", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("leadership_memos")
    op.drop_table("platform_leads")
