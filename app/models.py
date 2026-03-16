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


class ThemeStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    DEFERRED = "DEFERRED"
    CANCELLED = "CANCELLED"


class InitiativeStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    DEFERRED = "DEFERRED"
    CANCELLED = "CANCELLED"


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


class MemoStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"
    SENT = "SENT"


class UpdateStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"


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
    initiative_links = relationship(
        "InitiativeCommitmentLink", back_populates="commitment", cascade="all, delete-orphan",
        lazy="select",
    )

    # Strategic signal fields (Feature 021)
    strategic_contribution_note = Column(Text, nullable=True)
    execution_impact_note = Column(Text, nullable=True)

    strategic_signals = relationship(
        "StrategicSignal", back_populates="commitment", cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Commitment {self.id} title={self.title!r} status={self.status}>"


# ---------------------------------------------------------------------------
# Strategic Theme
# ---------------------------------------------------------------------------

class StrategicTheme(Base):
    __tablename__ = "strategic_themes"

    id = Column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    title = Column(String(512), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(ThemeStatus, name="theme_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=ThemeStatus.ACTIVE,
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

    initiatives = relationship(
        "Initiative", back_populates="theme",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<StrategicTheme {self.id} title={self.title!r} status={self.status}>"


# ---------------------------------------------------------------------------
# Initiative
# ---------------------------------------------------------------------------

class Initiative(Base):
    __tablename__ = "initiatives"

    id = Column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    title = Column(String(512), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(InitiativeStatus, name="initiative_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=InitiativeStatus.ACTIVE,
    )
    theme_id = Column(
        Uuid,
        ForeignKey("strategic_themes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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

    theme = relationship("StrategicTheme", back_populates="initiatives")
    commitment_links = relationship(
        "InitiativeCommitmentLink", back_populates="initiative", cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Initiative {self.id} title={self.title!r} status={self.status}>"


# ---------------------------------------------------------------------------
# Initiative-Commitment Link (join table)
# ---------------------------------------------------------------------------

class InitiativeCommitmentLink(Base):
    __tablename__ = "initiative_commitment_links"

    id = Column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    initiative_id = Column(
        Uuid,
        ForeignKey("initiatives.id", ondelete="CASCADE"),
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

    initiative = relationship("Initiative", back_populates="commitment_links")
    commitment = relationship("Commitment", back_populates="initiative_links")

    def __repr__(self) -> str:
        return f"<InitiativeCommitmentLink init={self.initiative_id} commit={self.commitment_id}>"


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


# ---------------------------------------------------------------------------
# Platform Lead
# ---------------------------------------------------------------------------

class PlatformLead(Base):
    __tablename__ = "platform_leads"

    id = Column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    name = Column(String(256), nullable=False, index=True)
    role = Column(String(512), nullable=False)
    focus_area = Column(String(512), nullable=False)
    email = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    initiative_ids = Column(Text, nullable=True)  # JSON array of initiative UUIDs
    active = Column(
        Integer,
        nullable=False,
        default=1,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<PlatformLead {self.id} name={self.name!r} role={self.role!r}>"


# ---------------------------------------------------------------------------
# Leadership Memo
# ---------------------------------------------------------------------------

class LeadershipMemo(Base):
    __tablename__ = "leadership_memos"

    id = Column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    week_start_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    author = Column(String(256), nullable=True)
    status = Column(
        Enum(MemoStatus, name="memo_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=MemoStatus.DRAFT,
    )

    strategic_objective = Column(Text, nullable=True)
    current_priorities = Column(Text, nullable=True)  # JSON array
    progress_summary = Column(Text, nullable=True)
    focus_next_week = Column(Text, nullable=True)  # JSON array
    success_criteria = Column(Text, nullable=True)  # JSON array

    lead_updates = Column(Text, nullable=True)  # JSON object
    dashboard_snapshot = Column(Text, nullable=True)  # JSON object
    audience = Column(Text, nullable=True)  # JSON array

    def __repr__(self) -> str:
        return f"<LeadershipMemo {self.id} week={self.week_start_date} status={self.status}>"


# ---------------------------------------------------------------------------
# Weekly Strategy Update (Feature 020 — Friday Execution Update)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Strategic Signal (Feature 021 — Task Strategic Signal System)
# ---------------------------------------------------------------------------

class SignalEventType(str, enum.Enum):
    OPENED = "OPENED"
    CLOSED = "CLOSED"


class StrategicSignal(Base):
    __tablename__ = "strategic_signals"

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
    initiative_id = Column(
        Uuid,
        ForeignKey("initiatives.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    theme_id = Column(
        Uuid,
        ForeignKey("strategic_themes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type = Column(
        String(32),
        nullable=False,
    )  # OPENED or CLOSED
    strategic_contribution = Column(Text, nullable=True)
    execution_impact = Column(Text, nullable=True)
    is_high_signal = Column(Integer, nullable=False, default=0)
    signal_category = Column(String(128), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    commitment = relationship("Commitment", back_populates="strategic_signals")
    initiative = relationship("Initiative")
    theme = relationship("StrategicTheme")

    def __repr__(self) -> str:
        return f"<StrategicSignal {self.id} event={self.event_type} commitment={self.commitment_id}>"


class WeeklyStrategyUpdate(Base):
    __tablename__ = "weekly_strategy_updates"

    id = Column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    week_start_date = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    status = Column(
        Enum(UpdateStatus, name="update_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=UpdateStatus.DRAFT,
    )

    # Three narrative drafts (JSON: {framing, strategic_objective, why, behavior, body})
    narrative_options = Column(Text, nullable=True)  # JSON array of 3 narrative dicts
    recommended_narrative = Column(Integer, nullable=True)  # 0, 1, or 2

    # Strategy Confidence Score
    confidence_score = Column(Integer, nullable=True)  # 0-100
    confidence_trend = Column(String(32), nullable=True)  # "up", "down", "stable"
    confidence_explanation = Column(Text, nullable=True)

    # Score components (JSON: {execution, momentum, alignment, friction})
    score_components = Column(Text, nullable=True)  # JSON object

    # Strategic Narrative Continuity
    narrative_continuity = Column(Text, nullable=True)

    # Forwardable version (clean copy for Brian to forward)
    forwardable_body = Column(Text, nullable=True)

    # Signal snapshot (JSON: raw data used for generation)
    signal_snapshot = Column(Text, nullable=True)  # JSON object

    # Previous week reference for trend comparison
    previous_update_id = Column(
        Uuid,
        ForeignKey("weekly_strategy_updates.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<WeeklyStrategyUpdate {self.id} week={self.week_start_date} score={self.confidence_score}>"
