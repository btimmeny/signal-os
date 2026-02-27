"""Initial schema — commitments and reminders.

Revision ID: 001
Revises:
Create Date: 2026-02-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enums
    commitment_status = sa.Enum(
        "OPEN", "WAITING", "SNOOZED", "CLOSED", name="commitment_status"
    )
    urgency = sa.Enum("NOW", "SOON", "SCHEDULED", "SOMEDAY", name="urgency")
    channel_type = sa.Enum(
        "email", "slack", "meeting", "call", "text", "web", "other",
        name="channel_type",
    )

    op.create_table(
        "commitments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(512), nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", commitment_status, nullable=False, index=True),
        sa.Column("urgency", urgency, nullable=True),
        sa.Column("person", sa.String(256), nullable=True, index=True),
        sa.Column("organization", sa.String(256), nullable=True),
        sa.Column("channel_type", channel_type, nullable=True),
        sa.Column("channel_title", sa.String(256), nullable=True),
        sa.Column("channel_link", sa.String(1024), nullable=True),
        sa.Column("source_snippet", sa.Text, nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("last_touched_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "reminders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("commitment_id", UUID(as_uuid=True), sa.ForeignKey("commitments.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_channel", sa.String(64), nullable=False, server_default="whatsapp"),
        sa.Column("delivery_target", sa.String(256), nullable=True),
        sa.Column("message", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("reminders")
    op.drop_table("commitments")
    sa.Enum(name="commitment_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="urgency").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="channel_type").drop(op.get_bind(), checkfirst=True)
