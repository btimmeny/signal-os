"""SQLAlchemy ORM models for commitments, objectives, and reminders."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
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
    INCIDENT = "INCIDENT"
    NOW = "NOW"
    SOON = "SOON"
    SCHEDULED = "SCHEDULED"
    SOMEDAY = "SOMEDAY"
    ADMIN = "ADMIN"


class ChannelType(str, enum.Enum):
    EMAIL = "email"
    SLACK = "slack"
    MEETING = "meeting"
    CALL = "call"
    TEXT = "text"
    WEB = "web"
    OTHER = "other"


class ObjectiveStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    DEFERRED = "DEFERRED"
    CANCELLED = "CANCELLED"


class ReportPeriod(str, enum.Enum):
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"


# ---------------------------------------------------------------------------
# Commitment
# ---------------------------------------------------------------------------

class Commitment(Base):
    __tablename__ = "commitments"

    id = Column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    title = Column(String(512), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(CommitmentStatus, name="commitment_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=CommitmentStatus.OPEN,
        index=True,
    )
    urgency = Column(
        Enum(Urgency, name="urgency", values_callable=lambda e: [m.value for m in e]),
        nullable=True,
    )
    person = Column(String(256), nullable=True, index=True)
    organization = Column(String(256), nullable=True)
    channel_type = Column(
        Enum(ChannelType, name="channel_type", values_callable=lambda e: [m.value for m in e]),
        nullable=True,
    )
    channel_title = Column(String(256), nullable=True)
    channel_link = Column(String(1024), nullable=True)
    source_snippet = Column(Text, nullable=True)
    priority_order = Column(Integer, nullable=True)

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
    comments = relationship(
        "CommitmentComment", back_populates="commitment", cascade="all, delete-orphan",
        lazy="select",
        order_by="CommitmentComment.created_at.asc()",
    )
    objective_links = relationship(
        "ObjectiveCommitmentLink", back_populates="commitment", cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Commitment {self.id} title={self.title!r} status={self.status}>"


# ---------------------------------------------------------------------------
# Commitment Comment
# ---------------------------------------------------------------------------

class CommitmentComment(Base):
    __tablename__ = "commitment_comments"

    id = Column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    commitment_id = Column(
        Uuid,
        ForeignKey("commitments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    body = Column(Text, nullable=False)
    author = Column(String(256), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    commitment = relationship("Commitment", back_populates="comments")

    def __repr__(self) -> str:
        return f"<CommitmentComment {self.id} commitment={self.commitment_id}>"


# ---------------------------------------------------------------------------
# Strategic Objective
# ---------------------------------------------------------------------------

class StrategicObjective(Base):
    __tablename__ = "strategic_objectives"

    id = Column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    title = Column(String(512), nullable=False, index=True)
    description = Column(Text, nullable=True)
    year = Column(Integer, nullable=False, index=True)
    status = Column(
        Enum(ObjectiveStatus, name="objective_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=ObjectiveStatus.ACTIVE,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    commitment_links = relationship(
        "ObjectiveCommitmentLink", back_populates="objective", cascade="all, delete-orphan",
        lazy="select",
    )
    updates = relationship(
        "ObjectiveUpdate", back_populates="objective", cascade="all, delete-orphan",
        lazy="select",
        order_by="ObjectiveUpdate.created_at.asc()",
    )

    def __repr__(self) -> str:
        return f"<StrategicObjective {self.id} title={self.title!r} year={self.year}>"


# ---------------------------------------------------------------------------
# Objective-Commitment Link (join table)
# ---------------------------------------------------------------------------

class ObjectiveCommitmentLink(Base):
    __tablename__ = "objective_commitment_links"

    id = Column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    objective_id = Column(
        Uuid,
        ForeignKey("strategic_objectives.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    commitment_id = Column(
        Uuid,
        ForeignKey("commitments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rationale = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    objective = relationship("StrategicObjective", back_populates="commitment_links")
    commitment = relationship("Commitment", back_populates="objective_links")

    def __repr__(self) -> str:
        return f"<ObjectiveCommitmentLink obj={self.objective_id} commit={self.commitment_id}>"


# ---------------------------------------------------------------------------
# Objective Update (general commentary on objectives)
# ---------------------------------------------------------------------------

class ObjectiveUpdate(Base):
    __tablename__ = "objective_updates"

    id = Column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    objective_id = Column(
        Uuid,
        ForeignKey("strategic_objectives.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    body = Column(Text, nullable=False)
    author = Column(String(256), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    objective = relationship("StrategicObjective", back_populates="updates")

    def __repr__(self) -> str:
        return f"<ObjectiveUpdate {self.id} objective={self.objective_id}>"


# ---------------------------------------------------------------------------
# Status Report
# ---------------------------------------------------------------------------

class StatusReport(Base):
    __tablename__ = "status_reports"

    id = Column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    period_type = Column(
        Enum(ReportPeriod, name="report_period", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<StatusReport {self.id} {self.period_type} {self.period_start}-{self.period_end}>"


# ---------------------------------------------------------------------------
# Reminder
# ---------------------------------------------------------------------------

class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    commitment_id = Column(
        Uuid,
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
