"""Business logic for commitment CRUD and queries."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Commitment, CommitmentStatus, ChannelType, Urgency

logger = logging.getLogger(__name__)


def open_commitment(
    db: Session,
    *,
    title: str,
    description: Optional[str] = None,
    person: Optional[str] = None,
    organization: Optional[str] = None,
    channel_type: Optional[str] = None,
    channel_title: Optional[str] = None,
    channel_link: Optional[str] = None,
    urgency: Optional[str] = None,
    due_at: Optional[datetime] = None,
    source_snippet: Optional[str] = None,
    status: str = "OPEN",
) -> Commitment:
    """Create a new commitment."""
    now = datetime.now(timezone.utc)
    c = Commitment(
        title=title,
        description=description,
        person=person,
        organization=organization,
        channel_type=ChannelType(channel_type) if channel_type else None,
        channel_title=channel_title,
        channel_link=channel_link,
        urgency=Urgency(urgency) if urgency else None,
        due_at=due_at,
        source_snippet=source_snippet,
        status=CommitmentStatus(status),
        opened_at=now,
        last_touched_at=now,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    logger.info("Opened commitment %s: %s", c.id, c.title)
    return c


def close_commitment(
    db: Session,
    *,
    commitment_id: Optional[str] = None,
    title: Optional[str] = None,
    person: Optional[str] = None,
) -> tuple[Optional[Commitment], list[Commitment]]:
    """Close a commitment by ID or by exact title (+person) match.

    Returns (closed_commitment, candidates).
    - If found exactly one match: (commitment, [])
    - If multiple matches: (None, list_of_candidates)
    - If no match: (None, [])
    """
    now = datetime.now(timezone.utc)

    if commitment_id:
        c = db.query(Commitment).filter(
            Commitment.id == commitment_id,
            Commitment.status != CommitmentStatus.CLOSED,
        ).first()
        if c:
            c.status = CommitmentStatus.CLOSED
            c.closed_at = now
            c.last_touched_at = now
            db.commit()
            db.refresh(c)
            logger.info("Closed commitment %s by ID", c.id)
            return c, []
        return None, []

    # Match by title (+ optional person)
    q = db.query(Commitment).filter(
        Commitment.title == title,
        Commitment.status != CommitmentStatus.CLOSED,
    )
    if person:
        q = q.filter(Commitment.person == person)

    candidates = q.all()
    if len(candidates) == 1:
        c = candidates[0]
        c.status = CommitmentStatus.CLOSED
        c.closed_at = now
        c.last_touched_at = now
        db.commit()
        db.refresh(c)
        logger.info("Closed commitment %s by title match", c.id)
        return c, []
    if len(candidates) > 1:
        return None, candidates
    return None, []


def update_commitment(
    db: Session,
    *,
    commitment_id: str,
    **fields,
) -> Optional[Commitment]:
    """Update partial fields on a commitment."""
    c = db.query(Commitment).filter(
        Commitment.id == commitment_id,
    ).first()
    if not c:
        return None

    for key, value in fields.items():
        if value is None:
            continue
        if key == "status":
            value = CommitmentStatus(value)
            if value == CommitmentStatus.CLOSED:
                c.closed_at = datetime.now(timezone.utc)
        elif key == "urgency":
            value = Urgency(value)
        elif key == "channel_type":
            value = ChannelType(value)
        setattr(c, key, value)

    c.last_touched_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    logger.info("Updated commitment %s", c.id)
    return c


def list_open(db: Session) -> list[Commitment]:
    """Return all non-CLOSED commitments, oldest opened first."""
    return (
        db.query(Commitment)
        .filter(Commitment.status != CommitmentStatus.CLOSED)
        .order_by(Commitment.opened_at.asc())
        .all()
    )


def query_commitments(
    db: Session,
    *,
    person: Optional[str] = None,
    status: Optional[str] = None,
    urgency: Optional[str] = None,
    channel_type: Optional[str] = None,
    due_before: Optional[datetime] = None,
    due_after: Optional[datetime] = None,
    opened_before: Optional[datetime] = None,
    opened_after: Optional[datetime] = None,
    text: Optional[str] = None,
) -> list[Commitment]:
    """Flexible query with optional filters."""
    q = db.query(Commitment)

    if person:
        q = q.filter(Commitment.person.ilike(f"%{person}%"))
    if status:
        q = q.filter(Commitment.status == CommitmentStatus(status))
    if urgency:
        q = q.filter(Commitment.urgency == Urgency(urgency))
    if channel_type:
        q = q.filter(Commitment.channel_type == ChannelType(channel_type))
    if due_before:
        q = q.filter(Commitment.due_at <= due_before)
    if due_after:
        q = q.filter(Commitment.due_at >= due_after)
    if opened_before:
        q = q.filter(Commitment.opened_at <= opened_before)
    if opened_after:
        q = q.filter(Commitment.opened_at >= opened_after)
    if text:
        pattern = f"%{text}%"
        q = q.filter(
            or_(
                Commitment.title.ilike(pattern),
                Commitment.description.ilike(pattern),
            )
        )

    return q.order_by(Commitment.opened_at.asc()).all()
