"""SQLAlchemy ORM models for commitments and reminders."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CommitmentStatus(str, enum.Enum):
    OPEN = "OPEN"
    WAITING = "WAITING"
    SNOOZED = "SNOOZED"
    CLOSED = "CLOSED"


class Urgency(str, enum.Enum):
    NOW = "NOW"
    SOON = "SOON"
    SCHEDULED = "SCHEDULED"
    SOMEDAY = "SOMEDAY"


class ChannelType(str, enum.Enum):
    EMAIL = "email"
    SLACK = "slack"
    MEETING = "meeting"
    CALL = "call"
    TEXT = "text"
    WEB = "web"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Commitment
# ---------------------------------------------------------------------------

class Commitment(Base):
    __tablename__ = "commitments"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    title = Column(String(512), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(CommitmentStatus, name="commitment_status"),
        nullable=False,
        default=CommitmentStatus.OPEN,
        index=True,
    )
    urgency = Column(
        Enum(Urgency, name="urgency"),
        nullable=True,
    )
    person = Column(String(256), nullable=True, index=True)
    organization = Column(String(256), nullable=True)
    channel_type = Column(
        Enum(ChannelType, name="channel_type"),
        nullable=True,
    )
    channel_title = Column(String(256), nullable=True)
    channel_link = Column(String(1024), nullable=True)
    source_snippet = Column(Text, nullable=True)

    opened_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    closed_at = Column(DateTime(timezone=True), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_touched_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    reminders = relationship(
        "Reminder", back_populates="commitment", cascade="all, delete-orphan",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<Commitment {self.id} title={self.title!r} status={self.status}>"


# ---------------------------------------------------------------------------
# Reminder
# ---------------------------------------------------------------------------

class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    commitment_id = Column(
        String(36),
        ForeignKey("commitments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    remind_at = Column(DateTime(timezone=True), nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivery_channel = Column(String(64), nullable=False, default="whatsapp")
    delivery_target = Column(String(256), nullable=True)
    message = Column(Text, nullable=True)

    commitment = relationship("Commitment", back_populates="reminders")

    def __repr__(self) -> str:
        return f"<Reminder {self.id} for={self.commitment_id} at={self.remind_at}>"
