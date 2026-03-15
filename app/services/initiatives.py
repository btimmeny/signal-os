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
    theme_id: Optional[str] = None,
) -> Initiative:
    """Create a new initiative."""
    init = Initiative(
        id=uuid.uuid4(),
        title=title,
        description=description,
        status=InitiativeStatus(status),
        theme_id=uuid.UUID(theme_id) if theme_id else None,
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
            elif k == "theme_id":
                v = uuid.UUID(v) if isinstance(v, str) else v
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


def seed_initiatives(
    db: Session,
    *,
    titles: list[str],
) -> list[Initiative]:
    """Seed initiatives from a list of titles.

    Skips titles that already exist (case-insensitive match).
    Returns all created initiatives.
    """
    existing = {i.title.lower() for i in db.query(Initiative).all()}
    created: list[Initiative] = []
    for title in titles:
        if title.lower() not in existing:
            init = Initiative(
                id=uuid.uuid4(),
                title=title,
                status=InitiativeStatus.ACTIVE,
            )
            db.add(init)
            created.append(init)
    if created:
        db.commit()
        for init in created:
            db.refresh(init)
    return created


def get_initiative_task_count(db: Session, *, initiative_id: str) -> int:
    """Return the number of open (non-CLOSED) commitments linked to an initiative."""
    from app.models import Commitment, CommitmentStatus, InitiativeCommitmentLink
    return (
        db.query(InitiativeCommitmentLink)
        .join(Commitment, InitiativeCommitmentLink.commitment_id == Commitment.id)
        .filter(
            InitiativeCommitmentLink.initiative_id == uuid.UUID(initiative_id),
            Commitment.status != CommitmentStatus.CLOSED,
        )
        .count()
    )
