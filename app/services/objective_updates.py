"""Business logic for objective updates (general commentary)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import ObjectiveUpdate, StrategicObjective

logger = logging.getLogger(__name__)


def add_update(
    db: Session,
    *,
    objective_id: str,
    body: str,
    author: Optional[str] = None,
) -> Optional[ObjectiveUpdate]:
    """Add an update to an objective.

    Returns the new update, or None if the objective does not exist.
    """
    obj = db.query(StrategicObjective).filter(
        StrategicObjective.id == uuid.UUID(objective_id),
    ).first()
    if not obj:
        return None

    update = ObjectiveUpdate(
        objective_id=obj.id,
        body=body,
        author=author,
        created_at=datetime.now(timezone.utc),
    )
    db.add(update)

    obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(update)
    logger.info("Added update %s to objective %s", update.id, obj.id)
    return update


def list_updates(
    db: Session,
    *,
    objective_id: str,
) -> Optional[list[ObjectiveUpdate]]:
    """List all updates for an objective, ordered oldest first.

    Returns None if the objective does not exist.
    """
    obj = db.query(StrategicObjective).filter(
        StrategicObjective.id == uuid.UUID(objective_id),
    ).first()
    if not obj:
        return None

    return (
        db.query(ObjectiveUpdate)
        .filter(ObjectiveUpdate.objective_id == obj.id)
        .order_by(ObjectiveUpdate.created_at.asc())
        .all()
    )
