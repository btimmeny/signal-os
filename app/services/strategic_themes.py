"""CRUD operations for strategic themes."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models import StrategicTheme, ThemeStatus


def create_theme(
    db: Session,
    *,
    title: str,
    description: Optional[str] = None,
    status: str = "ACTIVE",
) -> StrategicTheme:
    """Create a new strategic theme."""
    theme = StrategicTheme(
        id=uuid.uuid4(),
        title=title,
        description=description,
        status=ThemeStatus(status),
    )
    db.add(theme)
    db.commit()
    db.refresh(theme)
    return theme


def update_theme(
    db: Session,
    *,
    theme_id: str,
    **fields,
) -> Optional[StrategicTheme]:
    """Update a theme by ID. Returns None if not found."""
    theme = db.query(StrategicTheme).filter(StrategicTheme.id == uuid.UUID(theme_id)).first()
    if not theme:
        return None

    for k, v in fields.items():
        if v is not None:
            if k == "status":
                v = ThemeStatus(v)
            setattr(theme, k, v)

    db.commit()
    db.refresh(theme)
    return theme


def list_themes(
    db: Session,
    *,
    status: Optional[str] = None,
) -> list[StrategicTheme]:
    """List themes, optionally filtered by status."""
    q = db.query(StrategicTheme)
    if status:
        q = q.filter(StrategicTheme.status == ThemeStatus(status))
    return q.order_by(StrategicTheme.created_at.asc()).all()


def get_theme(
    db: Session,
    *,
    theme_id: str,
) -> Optional[StrategicTheme]:
    """Get a single theme by ID."""
    return db.query(StrategicTheme).filter(StrategicTheme.id == uuid.UUID(theme_id)).first()


def seed_themes(
    db: Session,
    *,
    themes: list[dict],
) -> list[StrategicTheme]:
    """Seed themes from a list of {title, description} dicts.

    Skips titles that already exist (case-insensitive match).
    Returns all created themes.
    """
    existing = {t.title.lower() for t in db.query(StrategicTheme).all()}
    created: list[StrategicTheme] = []
    for theme_data in themes:
        title = theme_data.get("title", "")
        if not title or title.lower() in existing:
            continue
        theme = StrategicTheme(
            id=uuid.uuid4(),
            title=title,
            description=theme_data.get("description"),
            status=ThemeStatus.ACTIVE,
        )
        db.add(theme)
        created.append(theme)
        existing.add(title.lower())
    if created:
        db.commit()
        for theme in created:
            db.refresh(theme)
    return created
