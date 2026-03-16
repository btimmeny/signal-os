"""Add email column to platform_leads.

Revision ID: 013
"""

from alembic import op
import sqlalchemy as sa


revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("platform_leads", sa.Column("email", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("platform_leads", "email")
