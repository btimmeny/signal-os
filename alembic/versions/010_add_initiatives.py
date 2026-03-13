"""Add initiatives and initiative_commitment_links tables.

Revision ID: 010
"""

from alembic import op
import sqlalchemy as sa


revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "initiatives",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "COMPLETED", "DEFERRED", "CANCELLED", name="initiative_status"),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "initiative_commitment_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "initiative_id",
            sa.Uuid(),
            sa.ForeignKey("initiatives.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "commitment_id",
            sa.Uuid(),
            sa.ForeignKey("commitments.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("initiative_commitment_links")
    op.drop_table("initiatives")
