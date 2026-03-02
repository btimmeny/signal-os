"""Business logic for strategic objectives."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import StrategicObjective, ObjectiveStatus

logger = logging.getLogger(__name__)


def create_objective(
    db: Session,
    *,
    title: str,
    description: Optional[str] = None,
    year: int,
    status: str = "ACTIVE",
) -> StrategicObjective:
    """Create a new strategic objective."""
    obj = StrategicObjective(
        title=title,
        description=description,
        year=year,
        status=ObjectiveStatus(status),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    logger.info("Created objective %s: %s (year=%d)", obj.id, title, year)
    return obj


def update_objective(
    db: Session,
    *,
    objective_id: str,
    **fields,
) -> Optional[StrategicObjective]:
    """Update fields on an existing objective."""
    obj = db.query(StrategicObjective).filter(
        StrategicObjective.id == uuid.UUID(objective_id),
    ).first()
    if not obj:
        return None

    for key, value in fields.items():
        if value is not None:
            if key == "status":
                value = ObjectiveStatus(value)
            setattr(obj, key, value)

    obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    logger.info("Updated objective %s", obj.id)
    return obj


def get_objective(
    db: Session,
    *,
    objective_id: str,
) -> Optional[StrategicObjective]:
    """Get a single objective by ID."""
    return db.query(StrategicObjective).filter(
        StrategicObjective.id == uuid.UUID(objective_id),
    ).first()


def list_objectives(
    db: Session,
    *,
    year: Optional[int] = None,
    status: Optional[str] = None,
) -> list[StrategicObjective]:
    """List objectives, optionally filtered by year and/or status."""
    q = db.query(StrategicObjective)
    if year is not None:
        q = q.filter(StrategicObjective.year == year)
    if status is not None:
        q = q.filter(StrategicObjective.status == ObjectiveStatus(status))
    return q.order_by(StrategicObjective.year.desc(), StrategicObjective.title).all()
