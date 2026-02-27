"""Pydantic request / response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, computed_field


# ---------------------------------------------------------------------------
# Enums (mirror SQLAlchemy enums for the API layer)
# ---------------------------------------------------------------------------

class CommitmentStatus(str, Enum):
    OPEN = "OPEN"
    WAITING = "WAITING"
    SNOOZED = "SNOOZED"
    CLOSED = "CLOSED"


class Urgency(str, Enum):
    NOW = "NOW"
    SOON = "SOON"
    SCHEDULED = "SCHEDULED"
    SOMEDAY = "SOMEDAY"


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
            opened_at=obj.opened_at,
            closed_at=obj.closed_at,
            due_at=obj.due_at,
            last_touched_at=obj.last_touched_at,
            days_open=round(delta, 2),
        )


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
