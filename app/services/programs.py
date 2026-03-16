"""CRUD operations for programs (workstreams under initiatives)."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Program, ProgramStatus


def create_program(
    db: Session,
    *,
    initiative_id: str,
    title: str,
    description: Optional[str] = None,
    owner: Optional[str] = None,
    status: str = "ACTIVE",
) -> Program:
    """Create a new program under an initiative."""
    prog = Program(
        id=uuid.uuid4(),
        initiative_id=uuid.UUID(initiative_id),
        title=title,
        description=description,
        owner=owner,
        status=ProgramStatus(status),
    )
    db.add(prog)
    db.commit()
    db.refresh(prog)
    return prog


def update_program(
    db: Session,
    *,
    program_id: str,
    **fields,
) -> Optional[Program]:
    """Update a program by ID. Returns None if not found."""
    prog = db.query(Program).filter(Program.id == uuid.UUID(program_id)).first()
    if not prog:
        return None

    for k, v in fields.items():
        if v is not None:
            if k == "status":
                v = ProgramStatus(v)
            elif k == "initiative_id":
                v = uuid.UUID(v) if isinstance(v, str) else v
            setattr(prog, k, v)

    db.commit()
    db.refresh(prog)
    return prog


def list_programs(
    db: Session,
    *,
    initiative_id: Optional[str] = None,
    status: Optional[str] = None,
) -> list[Program]:
    """List programs, optionally filtered by initiative and/or status."""
    q = db.query(Program)
    if initiative_id:
        q = q.filter(Program.initiative_id == uuid.UUID(initiative_id))
    if status:
        q = q.filter(Program.status == ProgramStatus(status))
    return q.order_by(Program.created_at.asc()).all()


def get_program(
    db: Session,
    *,
    program_id: str,
) -> Optional[Program]:
    """Get a single program by ID."""
    return db.query(Program).filter(Program.id == uuid.UUID(program_id)).first()
