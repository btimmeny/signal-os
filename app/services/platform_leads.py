"""CRUD operations for platform leads."""

from __future__ import annotations

import json
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models import PlatformLead


def create_lead(
    db: Session,
    *,
    name: str,
    role: str,
    focus_area: str,
    email: Optional[str] = None,
    description: Optional[str] = None,
    initiative_ids: Optional[list[str]] = None,
    active: bool = True,
) -> PlatformLead:
    """Create a new platform lead."""
    lead = PlatformLead(
        id=uuid.uuid4(),
        name=name,
        role=role,
        focus_area=focus_area,
        email=email,
        description=description,
        initiative_ids=json.dumps(initiative_ids) if initiative_ids else None,
        active=1 if active else 0,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def update_lead(
    db: Session,
    *,
    lead_id: str,
    **fields,
) -> Optional[PlatformLead]:
    """Update a platform lead by ID. Returns None if not found."""
    lead = db.query(PlatformLead).filter(PlatformLead.id == uuid.UUID(lead_id)).first()
    if not lead:
        return None

    for k, v in fields.items():
        if v is not None:
            if k == "initiative_ids":
                v = json.dumps(v) if isinstance(v, list) else v
            elif k == "active":
                v = 1 if v else 0
            setattr(lead, k, v)

    db.commit()
    db.refresh(lead)
    return lead


def list_leads(
    db: Session,
    *,
    active_only: bool = False,
) -> list[PlatformLead]:
    """List platform leads, optionally filtered to active only."""
    q = db.query(PlatformLead)
    if active_only:
        q = q.filter(PlatformLead.active == 1)
    return q.order_by(PlatformLead.created_at.asc()).all()


def get_lead(
    db: Session,
    *,
    lead_id: str,
) -> Optional[PlatformLead]:
    """Get a single platform lead by ID."""
    return db.query(PlatformLead).filter(PlatformLead.id == uuid.UUID(lead_id)).first()


def seed_leads(
    db: Session,
    *,
    leads: list[dict],
) -> list[PlatformLead]:
    """Seed platform leads from a list of dicts.

    Skips names that already exist (case-insensitive match).
    Returns all created leads.
    """
    existing = {l.name.lower() for l in db.query(PlatformLead).all()}
    created: list[PlatformLead] = []
    for lead_data in leads:
        name = lead_data.get("name", "")
        if not name or name.lower() in existing:
            continue
        lead = PlatformLead(
            id=uuid.uuid4(),
            name=name,
            role=lead_data.get("role", ""),
            focus_area=lead_data.get("focus_area", ""),
            email=lead_data.get("email"),
            description=lead_data.get("description"),
            initiative_ids=json.dumps(lead_data["initiative_ids"]) if lead_data.get("initiative_ids") else None,
            active=1,
        )
        db.add(lead)
        created.append(lead)
        existing.add(name.lower())
    if created:
        db.commit()
        for lead in created:
            db.refresh(lead)
    return created
