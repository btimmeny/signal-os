"""Add INCIDENT value to urgency enum.

Revision ID: 002
Revises: 001
Create Date: 2026-03-02
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE urgency ADD VALUE IF NOT EXISTS 'INCIDENT' BEFORE 'NOW'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums.
    # To fully reverse this, you would need to recreate the enum type
    # and migrate the column, which is out of scope for a downgrade.
    pass
