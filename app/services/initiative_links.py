"""Link / unlink commitments to initiatives."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Commitment, Initiative, InitiativeCommitmentLink


def link_commitment(
    db: Session,
    *,
    initiative_id: str,
    commitment_id: str,
    rationale: Optional[str] = None,
) -> Optional[InitiativeCommitmentLink]:
    """Link a commitment to an initiative. Idempotent — relinking updates rationale."""
    init = db.query(Initiative).filter(Initiative.id == uuid.UUID(initiative_id)).first()
    commit = db.query(Commitment).filter(Commitment.id == uuid.UUID(commitment_id)).first()
    if not init or not commit:
        return None

    existing = (
        db.query(InitiativeCommitmentLink)
        .filter(
            InitiativeCommitmentLink.initiative_id == uuid.UUID(initiative_id),
            InitiativeCommitmentLink.commitment_id == uuid.UUID(commitment_id),
        )
        .first()
    )
    if existing:
        existing.rationale = rationale
        db.commit()
        db.refresh(existing)
        return existing

    link = InitiativeCommitmentLink(
        id=uuid.uuid4(),
        initiative_id=uuid.UUID(initiative_id),
        commitment_id=uuid.UUID(commitment_id),
        rationale=rationale,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def unlink_commitment(
    db: Session,
    *,
    initiative_id: str,
    commitment_id: str,
) -> bool:
    """Remove link between commitment and initiative. Returns True if found."""
    link = (
        db.query(InitiativeCommitmentLink)
        .filter(
            InitiativeCommitmentLink.initiative_id == uuid.UUID(initiative_id),
            InitiativeCommitmentLink.commitment_id == uuid.UUID(commitment_id),
        )
        .first()
    )
    if not link:
        return False
    db.delete(link)
    db.commit()
    return True


def list_links_for_initiative(
    db: Session,
    *,
    initiative_id: str,
) -> Optional[list[InitiativeCommitmentLink]]:
    """List all commitment links for an initiative. Returns None if initiative not found."""
    init = db.query(Initiative).filter(Initiative.id == uuid.UUID(initiative_id)).first()
    if not init:
        return None
    return (
        db.query(InitiativeCommitmentLink)
        .filter(InitiativeCommitmentLink.initiative_id == uuid.UUID(initiative_id))
        .order_by(InitiativeCommitmentLink.created_at.asc())
        .all()
    )


def list_links_for_commitment(
    db: Session,
    *,
    commitment_id: str,
) -> Optional[list[InitiativeCommitmentLink]]:
    """List all initiative links for a commitment. Returns None if commitment not found."""
    commit = db.query(Commitment).filter(Commitment.id == uuid.UUID(commitment_id)).first()
    if not commit:
        return None
    return (
        db.query(InitiativeCommitmentLink)
        .filter(InitiativeCommitmentLink.commitment_id == uuid.UUID(commitment_id))
        .order_by(InitiativeCommitmentLink.created_at.asc())
        .all()
    )
