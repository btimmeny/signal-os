"""CRUD operations for initiatives."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Initiative, InitiativeStatus


def create_initiative(
    db: Session,
    *,
    title: str,
    description: Optional[str] = None,
    status: str = "ACTIVE",
) -> Initiative:
    """Create a new initiative."""
    init = Initiative(
        id=uuid.uuid4(),
        title=title,
        description=description,
        status=InitiativeStatus(status),
    )
    db.add(init)
    db.commit()
    db.refresh(init)
    return init


def update_initiative(
    db: Session,
    *,
    initiative_id: str,
    **fields,
) -> Optional[Initiative]:
    """Update an initiative by ID. Returns None if not found."""
    init = db.query(Initiative).filter(Initiative.id == uuid.UUID(initiative_id)).first()
    if not init:
        return None

    for k, v in fields.items():
        if v is not None:
            if k == "status":
                v = InitiativeStatus(v)
            setattr(init, k, v)

    db.commit()
    db.refresh(init)
    return init


def list_initiatives(
    db: Session,
    *,
    status: Optional[str] = None,
) -> list[Initiative]:
    """List initiatives, optionally filtered by status."""
    q = db.query(Initiative)
    if status:
        q = q.filter(Initiative.status == InitiativeStatus(status))
    return q.order_by(Initiative.created_at.asc()).all()


def get_initiative(
    db: Session,
    *,
    initiative_id: str,
) -> Optional[Initiative]:
    """Get a single initiative by ID."""
    return db.query(Initiative).filter(Initiative.id == uuid.UUID(initiative_id)).first()
