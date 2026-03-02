"""Add strategic_objectives table.

Revision ID: 006
Revises: 005
Create Date: 2026-03-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "strategic_objectives",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=False, index=True),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "COMPLETED", "DEFERRED", "CANCELLED", name="objective_status"),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("strategic_objectives")
    op.execute("DROP TYPE IF EXISTS objective_status")
