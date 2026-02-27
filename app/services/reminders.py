"""Business logic for reminder CRUD and dispatch."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.integrations.whatsapp import send_whatsapp
from app.models import Reminder

logger = logging.getLogger(__name__)


def create_reminder(
    db: Session,
    *,
    commitment_id: str,
    remind_at: datetime,
    message: Optional[str] = None,
    delivery_target: Optional[str] = None,
    delivery_channel: str = "whatsapp",
) -> Reminder:
    """Schedule a new reminder for a commitment."""
    r = Reminder(
        commitment_id=uuid.UUID(commitment_id),
        remind_at=remind_at,
        message=message,
        delivery_target=delivery_target,
        delivery_channel=delivery_channel,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    logger.info("Created reminder %s for commitment %s at %s", r.id, commitment_id, remind_at)
    return r


def get_due_reminders(db: Session) -> list[Reminder]:
    """Return all reminders where remind_at <= now and sent_at is NULL."""
    now = datetime.now(timezone.utc)
    return (
        db.query(Reminder)
        .filter(Reminder.remind_at <= now, Reminder.sent_at.is_(None))
        .order_by(Reminder.remind_at.asc())
        .all()
    )


def dispatch_due_reminders(db: Session) -> list[Reminder]:
    """Find all due reminders, 'send' them via integration, mark sent."""
    due = get_due_reminders(db)
    dispatched: list[Reminder] = []

    for r in due:
        commitment_title = r.commitment.title if r.commitment else "unknown"
        body = r.message or f"Reminder: {commitment_title}"
        target = r.delivery_target or "default"

        try:
            send_whatsapp(target=target, message=body)
            r.sent_at = datetime.now(timezone.utc)
            dispatched.append(r)
            logger.info("Dispatched reminder %s to %s via %s", r.id, target, r.delivery_channel)
        except Exception as e:
            logger.error("Failed to dispatch reminder %s: %s", r.id, e)

    if dispatched:
        db.commit()
        for r in dispatched:
            db.refresh(r)

    return dispatched
