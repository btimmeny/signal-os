"""Add status_reports table.

Revision ID: 009
Revises: 008
Create Date: 2026-03-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "status_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "period_type",
            sa.Enum("WEEKLY", "MONTHLY", "QUARTERLY", "ANNUAL", name="report_period"),
            nullable=False,
        ),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("status_reports")
    op.execute("DROP TYPE IF EXISTS report_period")
