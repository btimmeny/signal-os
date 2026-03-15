"""Pydantic request / response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums (mirror SQLAlchemy enums for the API layer)
# ---------------------------------------------------------------------------

class CommitmentStatus(str, Enum):
    OPEN = "OPEN"
    WAITING = "WAITING"
    SNOOZED = "SNOOZED"
    CLOSED = "CLOSED"


class Urgency(str, Enum):
    INCIDENT = "INCIDENT"
    NOW = "NOW"
    SOON = "SOON"
    SCHEDULED = "SCHEDULED"
    SOMEDAY = "SOMEDAY"
    ADMIN = "ADMIN"


class ChannelType(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    MEETING = "meeting"
    CALL = "call"
    TEXT = "text"
    WEB = "web"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Commitment schemas
# ---------------------------------------------------------------------------

class CommitmentOpenRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    description: Optional[str] = None
    person: Optional[str] = None
    organization: Optional[str] = None
    channel_type: Optional[ChannelType] = None
    channel_title: Optional[str] = None
    channel_link: Optional[str] = None
    urgency: Optional[Urgency] = None
    due_at: Optional[datetime] = None
    source_snippet: Optional[str] = None
    priority_order: Optional[int] = Field(None, ge=1)
    status: CommitmentStatus = CommitmentStatus.OPEN


class CommitmentCloseRequest(BaseModel):
    commitment_id: Optional[str] = None
    title: Optional[str] = None
    person: Optional[str] = None


class CommitmentUpdateRequest(BaseModel):
    commitment_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CommitmentStatus] = None
    urgency: Optional[Urgency] = None
    person: Optional[str] = None
    organization: Optional[str] = None
    channel_type: Optional[ChannelType] = None
    channel_title: Optional[str] = None
    channel_link: Optional[str] = None
    due_at: Optional[datetime] = None
    source_snippet: Optional[str] = None
    priority_order: Optional[int] = Field(None, ge=1)


class CommitmentSetPriorityRequest(BaseModel):
    commitment_id: str
    priority_order: int = Field(..., ge=1, description="Target position in the priority list (1 = top)")


class CommitmentResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: CommitmentStatus
    urgency: Optional[Urgency] = None
    person: Optional[str] = None
    organization: Optional[str] = None
    channel_type: Optional[ChannelType] = None
    channel_title: Optional[str] = None
    channel_link: Optional[str] = None
    source_snippet: Optional[str] = None
    priority_order: Optional[int] = None
    opened_at: datetime
    closed_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    last_touched_at: datetime
    days_open: float = 0.0

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_days(cls, obj) -> "CommitmentResponse":
        """Build response and compute days_open at read time."""
        now = datetime.now(timezone.utc)
        end = obj.closed_at or now
        # Normalize to aware datetimes (SQLite strips tzinfo)
        if hasattr(end, "tzinfo") and end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        opened = obj.opened_at.replace(tzinfo=timezone.utc) if obj.opened_at.tzinfo is None else obj.opened_at
        delta = (end - opened).total_seconds() / 86400.0
        return cls(
            id=str(obj.id),
            title=obj.title,
            description=obj.description,
            status=obj.status.value if hasattr(obj.status, "value") else obj.status,
            urgency=obj.urgency.value if obj.urgency and hasattr(obj.urgency, "value") else obj.urgency,
            person=obj.person,
            organization=obj.organization,
            channel_type=obj.channel_type.value if obj.channel_type and hasattr(obj.channel_type, "value") else obj.channel_type,
            channel_title=obj.channel_title,
            channel_link=obj.channel_link,
            source_snippet=obj.source_snippet,
            priority_order=obj.priority_order,
            opened_at=obj.opened_at,
            closed_at=obj.closed_at,
            due_at=obj.due_at,
            last_touched_at=obj.last_touched_at,
            days_open=round(delta, 2),
        )


# ---------------------------------------------------------------------------
# Comment schemas
# ---------------------------------------------------------------------------

class CommentCreateRequest(BaseModel):
    commitment_id: str
    body: str = Field(..., min_length=1)
    author: Optional[str] = None


class CommentResponse(BaseModel):
    id: str
    commitment_id: str
    body: str
    author: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_row(cls, obj) -> "CommentResponse":
        return cls(
            id=str(obj.id),
            commitment_id=str(obj.commitment_id),
            body=obj.body,
            author=obj.author,
            created_at=obj.created_at,
        )


# ---------------------------------------------------------------------------
# Strategic Theme schemas
# ---------------------------------------------------------------------------

class ThemeStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    DEFERRED = "DEFERRED"
    CANCELLED = "CANCELLED"


class ThemeCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    description: Optional[str] = None
    status: ThemeStatus = ThemeStatus.ACTIVE


class ThemeUpdateRequest(BaseModel):
    theme_id: str
    title: Optional[str] = Field(None, min_length=1, max_length=512)
    description: Optional[str] = None
    status: Optional[ThemeStatus] = None


class ThemeResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: ThemeStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_row(cls, obj) -> "ThemeResponse":
        return cls(
            id=str(obj.id),
            title=obj.title,
            description=obj.description,
            status=obj.status.value if hasattr(obj.status, "value") else obj.status,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )


class ThemeSeedRequest(BaseModel):
    themes: list[dict] = Field(..., min_length=1, description="List of {title, description} objects")


# ---------------------------------------------------------------------------
# Initiative schemas
# ---------------------------------------------------------------------------

class InitiativeStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    DEFERRED = "DEFERRED"
    CANCELLED = "CANCELLED"


class InitiativeCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    description: Optional[str] = None
    status: InitiativeStatus = InitiativeStatus.ACTIVE
    theme_id: Optional[str] = None


class InitiativeUpdateRequest(BaseModel):
    initiative_id: str
    title: Optional[str] = Field(None, min_length=1, max_length=512)
    description: Optional[str] = None
    status: Optional[InitiativeStatus] = None
    theme_id: Optional[str] = None


class InitiativeResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: InitiativeStatus
    theme_id: Optional[str] = None
    theme_title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_row(cls, obj) -> "InitiativeResponse":
        theme_title = None
        if hasattr(obj, 'theme') and obj.theme:
            theme_title = obj.theme.title
        return cls(
            id=str(obj.id),
            title=obj.title,
            description=obj.description,
            status=obj.status.value if hasattr(obj.status, "value") else obj.status,
            theme_id=str(obj.theme_id) if obj.theme_id else None,
            theme_title=theme_title,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )


class InitiativeSeedRequest(BaseModel):
    titles: list[str] = Field(..., min_length=1)


class InitiativeLinkRequest(BaseModel):
    initiative_id: str
    commitment_id: Optional[str] = None
    commitment_title: Optional[str] = None
    rationale: Optional[str] = None


class InitiativeLinkResponse(BaseModel):
    id: str
    initiative_id: str
    commitment_id: str
    rationale: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_row(cls, obj) -> "InitiativeLinkResponse":
        return cls(
            id=str(obj.id),
            initiative_id=str(obj.initiative_id),
            commitment_id=str(obj.commitment_id),
            rationale=obj.rationale,
            created_at=obj.created_at,
        )


# ---------------------------------------------------------------------------
# Strategic Objective schemas
# ---------------------------------------------------------------------------

class ObjectiveStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    DEFERRED = "DEFERRED"
    CANCELLED = "CANCELLED"


class ReportPeriod(str, Enum):
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"


class ObjectiveCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    description: Optional[str] = None
    year: int = Field(..., ge=2000, le=2100)
    status: ObjectiveStatus = ObjectiveStatus.ACTIVE


class ObjectiveUpdateRequest(BaseModel):
    objective_id: str
    title: Optional[str] = Field(None, min_length=1, max_length=512)
    description: Optional[str] = None
    year: Optional[int] = Field(None, ge=2000, le=2100)
    status: Optional[ObjectiveStatus] = None


class ObjectiveResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    year: int
    status: ObjectiveStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_row(cls, obj) -> "ObjectiveResponse":
        return cls(
            id=str(obj.id),
            title=obj.title,
            description=obj.description,
            year=obj.year,
            status=obj.status.value if hasattr(obj.status, "value") else obj.status,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )


# ---------------------------------------------------------------------------
# Objective-Commitment Link schemas
# ---------------------------------------------------------------------------

class ObjectiveLinkRequest(BaseModel):
    objective_id: str
    commitment_id: str
    rationale: Optional[str] = None


class ObjectiveLinkResponse(BaseModel):
    id: str
    objective_id: str
    commitment_id: str
    rationale: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_row(cls, obj) -> "ObjectiveLinkResponse":
        return cls(
            id=str(obj.id),
            objective_id=str(obj.objective_id),
            commitment_id=str(obj.commitment_id),
            rationale=obj.rationale,
            created_at=obj.created_at,
        )


# ---------------------------------------------------------------------------
# Objective Update schemas
# ---------------------------------------------------------------------------

class ObjectiveUpdateCreateRequest(BaseModel):
    objective_id: str
    body: str = Field(..., min_length=1)
    author: Optional[str] = None


class ObjectiveUpdateResponse(BaseModel):
    id: str
    objective_id: str
    body: str
    author: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_row(cls, obj) -> "ObjectiveUpdateResponse":
        return cls(
            id=str(obj.id),
            objective_id=str(obj.objective_id),
            body=obj.body,
            author=obj.author,
            created_at=obj.created_at,
        )


# ---------------------------------------------------------------------------
# Status Report schemas
# ---------------------------------------------------------------------------

class StatusReportCreateRequest(BaseModel):
    period_type: ReportPeriod
    period_start: datetime
    period_end: datetime
    body: str = Field(..., min_length=1)


class StatusReportResponse(BaseModel):
    id: str
    period_type: ReportPeriod
    period_start: datetime
    period_end: datetime
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_row(cls, obj) -> "StatusReportResponse":
        return cls(
            id=str(obj.id),
            period_type=obj.period_type.value if hasattr(obj.period_type, "value") else obj.period_type,
            period_start=obj.period_start,
            period_end=obj.period_end,
            body=obj.body,
            created_at=obj.created_at,
        )


class StatusDataRequest(BaseModel):
    period_type: ReportPeriod
    period_start: datetime
    period_end: datetime


# ---------------------------------------------------------------------------
# Reminder schemas
# ---------------------------------------------------------------------------

class ReminderCreateRequest(BaseModel):
    commitment_id: str
    remind_at: datetime
    message: Optional[str] = None
    delivery_target: Optional[str] = None
    delivery_channel: str = "whatsapp"


class ReminderResponse(BaseModel):
    id: str
    commitment_id: str
    remind_at: datetime
    sent_at: Optional[datetime] = None
    delivery_channel: str
    delivery_target: Optional[str] = None
    message: Optional[str] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_row(cls, obj) -> "ReminderResponse":
        return cls(
            id=str(obj.id),
            commitment_id=str(obj.commitment_id),
            remind_at=obj.remind_at,
            sent_at=obj.sent_at,
            delivery_channel=obj.delivery_channel,
            delivery_target=obj.delivery_target,
            message=obj.message,
        )
