"""Business logic for linking objectives to commitments."""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Commitment, ObjectiveCommitmentLink, StrategicObjective

logger = logging.getLogger(__name__)


def link_commitment(
    db: Session,
    *,
    objective_id: str,
    commitment_id: str,
    rationale: Optional[str] = None,
) -> Optional[ObjectiveCommitmentLink]:
    """Link a commitment to an objective.

    Returns None if the objective or commitment does not exist.
    Returns the existing link if already linked.
    """
    obj = db.query(StrategicObjective).filter(
        StrategicObjective.id == uuid.UUID(objective_id),
    ).first()
    if not obj:
        return None

    commit = db.query(Commitment).filter(
        Commitment.id == uuid.UUID(commitment_id),
    ).first()
    if not commit:
        return None

    # Check for existing link
    existing = db.query(ObjectiveCommitmentLink).filter(
        ObjectiveCommitmentLink.objective_id == obj.id,
        ObjectiveCommitmentLink.commitment_id == commit.id,
    ).first()
    if existing:
        # Update rationale if provided
        if rationale is not None:
            existing.rationale = rationale
            db.commit()
            db.refresh(existing)
        return existing

    link = ObjectiveCommitmentLink(
        objective_id=obj.id,
        commitment_id=commit.id,
        rationale=rationale,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    logger.info("Linked commitment %s to objective %s", commit.id, obj.id)
    return link


def unlink_commitment(
    db: Session,
    *,
    objective_id: str,
    commitment_id: str,
) -> bool:
    """Remove the link between a commitment and an objective.

    Returns True if a link was removed, False if no link existed.
    """
    link = db.query(ObjectiveCommitmentLink).filter(
        ObjectiveCommitmentLink.objective_id == uuid.UUID(objective_id),
        ObjectiveCommitmentLink.commitment_id == uuid.UUID(commitment_id),
    ).first()
    if not link:
        return False

    db.delete(link)
    db.commit()
    logger.info("Unlinked commitment %s from objective %s", commitment_id, objective_id)
    return True


def list_links_for_objective(
    db: Session,
    *,
    objective_id: str,
) -> Optional[list[ObjectiveCommitmentLink]]:
    """List all commitment links for an objective.

    Returns None if the objective does not exist.
    """
    obj = db.query(StrategicObjective).filter(
        StrategicObjective.id == uuid.UUID(objective_id),
    ).first()
    if not obj:
        return None

    return (
        db.query(ObjectiveCommitmentLink)
        .filter(ObjectiveCommitmentLink.objective_id == obj.id)
        .order_by(ObjectiveCommitmentLink.created_at.asc())
        .all()
    )


def list_links_for_commitment(
    db: Session,
    *,
    commitment_id: str,
) -> Optional[list[ObjectiveCommitmentLink]]:
    """List all objective links for a commitment.

    Returns None if the commitment does not exist.
    """
    commit = db.query(Commitment).filter(
        Commitment.id == uuid.UUID(commitment_id),
    ).first()
    if not commit:
        return None

    return (
        db.query(ObjectiveCommitmentLink)
        .filter(ObjectiveCommitmentLink.commitment_id == commit.id)
        .order_by(ObjectiveCommitmentLink.created_at.asc())
        .all()
    )
