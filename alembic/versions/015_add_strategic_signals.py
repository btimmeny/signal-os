"""Add strategic_signals table and contribution/impact notes to commitments.

Revision ID: 015
"""

from alembic import op
import sqlalchemy as sa


revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add strategic fields to commitments
    op.add_column("commitments", sa.Column("strategic_contribution_note", sa.Text(), nullable=True))
    op.add_column("commitments", sa.Column("execution_impact_note", sa.Text(), nullable=True))

    # Create strategic_signals table
    op.create_table(
        "strategic_signals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("commitment_id", sa.Uuid(), sa.ForeignKey("commitments.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("initiative_id", sa.Uuid(), sa.ForeignKey("initiatives.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("theme_id", sa.Uuid(), sa.ForeignKey("strategic_themes.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("event_type", sa.String(32), nullable=False),  # OPENED or CLOSED
        sa.Column("strategic_contribution", sa.Text(), nullable=True),
        sa.Column("execution_impact", sa.Text(), nullable=True),
        sa.Column("is_high_signal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("signal_category", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("strategic_signals")
    op.drop_column("commitments", "execution_impact_note")
    op.drop_column("commitments", "strategic_contribution_note")
