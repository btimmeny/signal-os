"""Add commitment_comments table.

Revision ID: 005
Revises: 004
Create Date: 2026-03-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commitment_comments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "commitment_id",
            sa.Uuid(),
            sa.ForeignKey("commitments.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("commitment_comments")
