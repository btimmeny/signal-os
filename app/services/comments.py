"""Business logic for commitment comments."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Commitment, CommitmentComment

logger = logging.getLogger(__name__)


def add_comment(
    db: Session,
    *,
    commitment_id: str,
    body: str,
    author: Optional[str] = None,
) -> Optional[CommitmentComment]:
    """Add a comment to a commitment.

    Returns the new comment, or None if the commitment does not exist.
    """
    c = db.query(Commitment).filter(
        Commitment.id == uuid.UUID(commitment_id),
    ).first()
    if not c:
        return None

    comment = CommitmentComment(
        commitment_id=c.id,
        body=body,
        author=author,
        created_at=datetime.now(timezone.utc),
    )
    db.add(comment)

    # Touch the parent commitment
    c.last_touched_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(comment)
    logger.info("Added comment %s to commitment %s", comment.id, c.id)
    return comment


def list_comments(
    db: Session,
    *,
    commitment_id: str,
) -> Optional[list[CommitmentComment]]:
    """List all comments for a commitment, ordered oldest first.

    Returns None if the commitment does not exist.
    Returns an empty list if the commitment exists but has no comments.
    """
    c = db.query(Commitment).filter(
        Commitment.id == uuid.UUID(commitment_id),
    ).first()
    if not c:
        return None

    return (
        db.query(CommitmentComment)
        .filter(CommitmentComment.commitment_id == c.id)
        .order_by(CommitmentComment.created_at.asc())
        .all()
    )
