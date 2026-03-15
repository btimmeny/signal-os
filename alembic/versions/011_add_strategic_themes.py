"""Add strategic_themes table and theme_id FK on initiatives.

Revision ID: 011
"""

from alembic import op
import sqlalchemy as sa


revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "strategic_themes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "COMPLETED", "DEFERRED", "CANCELLED", name="theme_status"),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.add_column(
        "initiatives",
        sa.Column(
            "theme_id",
            sa.Uuid(),
            sa.ForeignKey("strategic_themes.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("initiatives", "theme_id")
    op.drop_table("strategic_themes")
