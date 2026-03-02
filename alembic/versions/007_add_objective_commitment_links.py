"""Add objective_commitment_links table.

Revision ID: 007
Revises: 006
Create Date: 2026-03-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "objective_commitment_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "objective_id",
            sa.Uuid(),
            sa.ForeignKey("strategic_objectives.id", ondelete="CASCADE"),
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
    op.drop_table("objective_commitment_links")
