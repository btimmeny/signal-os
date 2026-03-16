"""Add programs table and execution fields to initiatives/commitments.

Revision ID: 018
"""

from alembic import op
import sqlalchemy as sa

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add owner to initiatives
    op.add_column("initiatives", sa.Column("owner", sa.String(256), nullable=True))

    # Create programs table
    op.create_table(
        "programs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "initiative_id",
            sa.Uuid(),
            sa.ForeignKey("initiatives.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(512), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner", sa.String(256), nullable=True),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Add execution fields to commitments
    op.add_column(
        "commitments",
        sa.Column(
            "initiative_id",
            sa.Uuid(),
            sa.ForeignKey("initiatives.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    op.add_column(
        "commitments",
        sa.Column(
            "program_id",
            sa.Uuid(),
            sa.ForeignKey("programs.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    op.add_column(
        "commitments",
        sa.Column("sequence_order", sa.Integer(), nullable=True),
    )
    op.add_column(
        "commitments",
        sa.Column(
            "depends_on_commitment_id",
            sa.Uuid(),
            sa.ForeignKey("commitments.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "commitments",
        sa.Column(
            "blocked_by_commitment_id",
            sa.Uuid(),
            sa.ForeignKey("commitments.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "commitments",
        sa.Column("milestone_flag", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "commitments",
        sa.Column(
            "completed_this_week", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "commitments",
        sa.Column("win_flag", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("commitments", "win_flag")
    op.drop_column("commitments", "completed_this_week")
    op.drop_column("commitments", "milestone_flag")
    op.drop_column("commitments", "blocked_by_commitment_id")
    op.drop_column("commitments", "depends_on_commitment_id")
    op.drop_column("commitments", "sequence_order")
    op.drop_column("commitments", "program_id")
    op.drop_column("commitments", "initiative_id")
    op.drop_table("programs")
    op.drop_column("initiatives", "owner")
