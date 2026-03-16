"""Add strategic execution intelligence tables.

Feature 022: Strategic Execution Intelligence System.

New tables:
- strategic_contribution_notes
- execution_impact_notes
- strategic_narratives
- strategy_confidence_history
- weekly_narratives

Extends:
- strategic_signals: add confidence_weight column

Revision ID: 016
"""

from alembic import op
import sqlalchemy as sa


revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add confidence_weight to strategic_signals
    op.add_column(
        "strategic_signals",
        sa.Column("confidence_weight", sa.Integer(), nullable=True, server_default="50"),
    )

    # Strategic Contribution Notes
    op.create_table(
        "strategic_contribution_notes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("commitments.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("initiative_id", sa.Uuid(), sa.ForeignKey("initiatives.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("strategic_theme", sa.String(256), nullable=True),
        sa.Column("strategic_contribution_note", sa.Text(), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="inferred"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Execution Impact Notes
    op.create_table(
        "execution_impact_notes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("commitments.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("initiative_id", sa.Uuid(), sa.ForeignKey("initiatives.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("execution_impact_note", sa.Text(), nullable=False),
        sa.Column("strategic_signal_flag", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Strategic Narratives (week-over-week strategic understanding)
    op.create_table(
        "strategic_narratives",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("strategic_objective", sa.Text(), nullable=True),
        sa.Column("strategic_themes", sa.Text(), nullable=True),
        sa.Column("momentum_signals", sa.Text(), nullable=True),
        sa.Column("friction_signals", sa.Text(), nullable=True),
        sa.Column("narrative_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Strategy Confidence History
    op.create_table(
        "strategy_confidence_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("previous_score", sa.Integer(), nullable=True),
        sa.Column("trend_direction", sa.String(32), nullable=True),
        sa.Column("confidence_explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Weekly Narratives (individual narrative drafts)
    op.create_table(
        "weekly_narratives",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("week_date", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("narrative_type", sa.String(64), nullable=False),
        sa.Column("strategic_objective", sa.Text(), nullable=True),
        sa.Column("narrative_text", sa.Text(), nullable=False),
        sa.Column("recommended_flag", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("weekly_narratives")
    op.drop_table("strategy_confidence_history")
    op.drop_table("strategic_narratives")
    op.drop_table("execution_impact_notes")
    op.drop_table("strategic_contribution_notes")
    op.drop_column("strategic_signals", "confidence_weight")
