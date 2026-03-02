"""Business logic for status reports."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    Commitment,
    CommitmentComment,
    ObjectiveCommitmentLink,
    ObjectiveUpdate,
    ReportPeriod,
    StatusReport,
    StrategicObjective,
)

logger = logging.getLogger(__name__)


def create_report(
    db: Session,
    *,
    period_type: str,
    period_start: datetime,
    period_end: datetime,
    body: str,
) -> StatusReport:
    """Store a generated status report."""
    report = StatusReport(
        period_type=ReportPeriod(period_type),
        period_start=period_start,
        period_end=period_end,
        body=body,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    logger.info("Created %s status report %s", period_type, report.id)
    return report


def list_reports(
    db: Session,
    *,
    period_type: Optional[str] = None,
) -> list[StatusReport]:
    """List status reports, optionally filtered by period type."""
    q = db.query(StatusReport)
    if period_type is not None:
        q = q.filter(StatusReport.period_type == ReportPeriod(period_type))
    return q.order_by(StatusReport.period_start.desc()).all()


def get_report(
    db: Session,
    *,
    report_id: str,
) -> Optional[StatusReport]:
    """Get a single report by ID."""
    return db.query(StatusReport).filter(
        StatusReport.id == uuid.UUID(report_id),
    ).first()


def gather_status_data(
    db: Session,
    *,
    period_start: datetime,
    period_end: datetime,
) -> dict:
    """Gather all data needed to produce a status report for a period.

    Returns a structured dict with:
    - objectives: all active objectives with their linked commitments and updates
    - commitment_activity: commitments opened, closed, or commented on during the period
    - objective_updates: objective updates created during the period
    """
    # Active objectives
    objectives = (
        db.query(StrategicObjective)
        .order_by(StrategicObjective.year.desc(), StrategicObjective.title)
        .all()
    )

    objective_data = []
    for obj in objectives:
        # Get linked commitments
        links = (
            db.query(ObjectiveCommitmentLink)
            .filter(ObjectiveCommitmentLink.objective_id == obj.id)
            .all()
        )
        linked_commitments = []
        for link in links:
            commit = db.query(Commitment).filter(
                Commitment.id == link.commitment_id,
            ).first()
            if commit:
                # Get comments in period
                period_comments = (
                    db.query(CommitmentComment)
                    .filter(
                        CommitmentComment.commitment_id == commit.id,
                        CommitmentComment.created_at >= period_start,
                        CommitmentComment.created_at <= period_end,
                    )
                    .order_by(CommitmentComment.created_at.asc())
                    .all()
                )
                linked_commitments.append({
                    "commitment_id": str(commit.id),
                    "title": commit.title,
                    "status": commit.status.value if hasattr(commit.status, "value") else commit.status,
                    "urgency": (commit.urgency.value if commit.urgency and hasattr(commit.urgency, "value") else commit.urgency),
                    "rationale": link.rationale,
                    "period_comments": [
                        {"body": c.body, "author": c.author, "created_at": c.created_at.isoformat()}
                        for c in period_comments
                    ],
                })

        # Get updates in period
        period_updates = (
            db.query(ObjectiveUpdate)
            .filter(
                ObjectiveUpdate.objective_id == obj.id,
                ObjectiveUpdate.created_at >= period_start,
                ObjectiveUpdate.created_at <= period_end,
            )
            .order_by(ObjectiveUpdate.created_at.asc())
            .all()
        )

        objective_data.append({
            "objective_id": str(obj.id),
            "title": obj.title,
            "description": obj.description,
            "year": obj.year,
            "status": obj.status.value if hasattr(obj.status, "value") else obj.status,
            "linked_commitments": linked_commitments,
            "period_updates": [
                {"body": u.body, "author": u.author, "created_at": u.created_at.isoformat()}
                for u in period_updates
            ],
        })

    # Commitment activity in period (opened or closed)
    opened_in_period = (
        db.query(Commitment)
        .filter(
            Commitment.opened_at >= period_start,
            Commitment.opened_at <= period_end,
        )
        .all()
    )
    closed_in_period = (
        db.query(Commitment)
        .filter(
            Commitment.closed_at >= period_start,
            Commitment.closed_at <= period_end,
        )
        .all()
    )

    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "objectives": objective_data,
        "commitments_opened": [
            {"id": str(c.id), "title": c.title, "urgency": (c.urgency.value if c.urgency and hasattr(c.urgency, "value") else c.urgency)}
            for c in opened_in_period
        ],
        "commitments_closed": [
            {"id": str(c.id), "title": c.title}
            for c in closed_in_period
        ],
    }
