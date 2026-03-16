"""Business logic for commitment CRUD and queries."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

import re

from app.models import (
    Commitment,
    CommitmentStatus,
    ChannelType,
    Initiative,
    InitiativeCommitmentLink,
    InitiativeStatus,
    ObjectiveCommitmentLink,
    Program,
    ProgramStatus,
    StrategicObjective,
    StrategicTheme,
    ThemeStatus,
    Urgency,
)

logger = logging.getLogger(__name__)


def _reorder_priorities(db: Session, target_position: int, exclude_id=None) -> None:
    """Shift existing priority_order values to make room at target_position.

    All non-CLOSED commitments with priority_order >= target_position are
    incremented by 1.  The optional *exclude_id* lets us skip the commitment
    that is being moved into that slot.
    """
    q = (
        db.query(Commitment)
        .filter(
            Commitment.status != CommitmentStatus.CLOSED,
            Commitment.priority_order.isnot(None),
            Commitment.priority_order >= target_position,
        )
    )
    if exclude_id is not None:
        q = q.filter(Commitment.id != exclude_id)

    for c in q.order_by(Commitment.priority_order.desc()).all():
        c.priority_order = c.priority_order + 1


def _compact_priorities(db: Session) -> None:
    """Re-number priority_order values to be contiguous starting from 1."""
    rows = (
        db.query(Commitment)
        .filter(
            Commitment.status != CommitmentStatus.CLOSED,
            Commitment.priority_order.isnot(None),
        )
        .order_by(Commitment.priority_order.asc())
        .all()
    )
    for idx, c in enumerate(rows, start=1):
        c.priority_order = idx


def open_commitment(
    db: Session,
    *,
    title: str,
    description: Optional[str] = None,
    person: Optional[str] = None,
    organization: Optional[str] = None,
    channel_type: Optional[str] = None,
    channel_title: Optional[str] = None,
    channel_link: Optional[str] = None,
    urgency: Optional[str] = None,
    due_at: Optional[datetime] = None,
    source_snippet: Optional[str] = None,
    status: str = "OPEN",
    priority_order: Optional[int] = None,
    initiative_id: Optional[str] = None,
    program_id: Optional[str] = None,
    sequence_order: Optional[int] = None,
    depends_on_commitment_id: Optional[str] = None,
    blocked_by_commitment_id: Optional[str] = None,
    milestone_flag: Optional[int] = 0,
    completed_this_week: Optional[int] = 0,
    win_flag: Optional[int] = 0,
) -> Commitment:
    """Create a new commitment."""
    now = datetime.now(timezone.utc)

    # If a priority_order is specified, shift existing items to make room
    if priority_order is not None:
        _reorder_priorities(db, priority_order)
        # Compact after insert to ensure contiguous numbering
        db.flush()

    c = Commitment(
        title=title,
        description=description,
        person=person,
        organization=organization,
        channel_type=ChannelType(channel_type) if channel_type else None,
        channel_title=channel_title,
        channel_link=channel_link,
        urgency=Urgency(urgency) if urgency else None,
        due_at=due_at,
        source_snippet=source_snippet,
        status=CommitmentStatus(status),
        priority_order=priority_order,
        initiative_id=uuid.UUID(initiative_id) if initiative_id else None,
        program_id=uuid.UUID(program_id) if program_id else None,
        sequence_order=sequence_order,
        depends_on_commitment_id=uuid.UUID(depends_on_commitment_id) if depends_on_commitment_id else None,
        blocked_by_commitment_id=uuid.UUID(blocked_by_commitment_id) if blocked_by_commitment_id else None,
        milestone_flag=milestone_flag or 0,
        completed_this_week=completed_this_week or 0,
        win_flag=win_flag or 0,
        opened_at=now,
        last_touched_at=now,
    )
    db.add(c)
    db.commit()
    if priority_order is not None:
        _compact_priorities(db)
        db.commit()
    db.refresh(c)
    logger.info("Opened commitment %s: %s", c.id, c.title)
    return c


def close_commitment(
    db: Session,
    *,
    commitment_id: Optional[str] = None,
    title: Optional[str] = None,
    person: Optional[str] = None,
) -> tuple[Optional[Commitment], list[Commitment]]:
    """Close a commitment by ID or by exact title (+person) match.

    Returns (closed_commitment, candidates).
    - If found exactly one match: (commitment, [])
    - If multiple matches: (None, list_of_candidates)
    - If no match: (None, [])
    """
    now = datetime.now(timezone.utc)

    if commitment_id:
        c = db.query(Commitment).filter(
            Commitment.id == uuid.UUID(commitment_id),
            Commitment.status != CommitmentStatus.CLOSED,
        ).first()
        if c:
            c.status = CommitmentStatus.CLOSED
            c.closed_at = now
            c.last_touched_at = now
            db.commit()
            db.refresh(c)
            logger.info("Closed commitment %s by ID", c.id)
            return c, []
        return None, []

    # Match by title (+ optional person)
    q = db.query(Commitment).filter(
        Commitment.title == title,
        Commitment.status != CommitmentStatus.CLOSED,
    )
    if person:
        q = q.filter(Commitment.person == person)

    candidates = q.all()
    if len(candidates) == 1:
        c = candidates[0]
        c.status = CommitmentStatus.CLOSED
        c.closed_at = now
        c.last_touched_at = now
        db.commit()
        db.refresh(c)
        logger.info("Closed commitment %s by title match", c.id)
        return c, []
    if len(candidates) > 1:
        return None, candidates
    return None, []


def update_commitment(
    db: Session,
    *,
    commitment_id: str,
    **fields,
) -> Optional[Commitment]:
    """Update partial fields on a commitment."""
    c = db.query(Commitment).filter(
        Commitment.id == uuid.UUID(commitment_id),
    ).first()
    if not c:
        return None

    # UUID fields that need conversion
    _uuid_fields = {"initiative_id", "program_id", "depends_on_commitment_id", "blocked_by_commitment_id"}

    for key, value in fields.items():
        if value is None:
            continue
        if key == "status":
            value = CommitmentStatus(value)
            if value == CommitmentStatus.CLOSED:
                c.closed_at = datetime.now(timezone.utc)
        elif key == "urgency":
            value = Urgency(value)
        elif key == "channel_type":
            value = ChannelType(value)
        elif key in _uuid_fields:
            value = uuid.UUID(value) if isinstance(value, str) else value
        elif key == "priority_order":
            old_pos = c.priority_order
            new_pos = value
            if old_pos is None:
                _reorder_priorities(db, new_pos, exclude_id=c.id)
            elif old_pos != new_pos:
                if new_pos < old_pos:
                    shift_q = (
                        db.query(Commitment)
                        .filter(
                            Commitment.status != CommitmentStatus.CLOSED,
                            Commitment.priority_order.isnot(None),
                            Commitment.priority_order >= new_pos,
                            Commitment.priority_order < old_pos,
                            Commitment.id != c.id,
                        )
                        .order_by(Commitment.priority_order.desc())
                        .all()
                    )
                    for item in shift_q:
                        item.priority_order = item.priority_order + 1
                else:
                    shift_q = (
                        db.query(Commitment)
                        .filter(
                            Commitment.status != CommitmentStatus.CLOSED,
                            Commitment.priority_order.isnot(None),
                            Commitment.priority_order > old_pos,
                            Commitment.priority_order <= new_pos,
                            Commitment.id != c.id,
                        )
                        .order_by(Commitment.priority_order.asc())
                        .all()
                    )
                    for item in shift_q:
                        item.priority_order = item.priority_order - 1
        setattr(c, key, value)

    c.last_touched_at = datetime.now(timezone.utc)
    db.commit()
    _compact_priorities(db)
    db.commit()
    db.refresh(c)
    logger.info("Updated commitment %s", c.id)
    return c


def set_priority(
    db: Session,
    *,
    commitment_id: str,
    priority_order: int,
) -> Optional[Commitment]:
    """Set a commitment's priority_order, shifting others as needed.

    Uses a proper move algorithm that handles both "move up" (to a lower
    position number) and "move down" (to a higher position number) correctly.
    For items that don't yet have a priority_order, this behaves as an insert.
    """
    c = db.query(Commitment).filter(
        Commitment.id == uuid.UUID(commitment_id),
    ).first()
    if not c:
        return None

    old_pos = c.priority_order
    new_pos = priority_order

    if old_pos is None:
        # Item has no priority yet — treat as insert
        _reorder_priorities(db, new_pos, exclude_id=c.id)
    elif old_pos == new_pos:
        # No-op
        pass
    elif new_pos < old_pos:
        # Moving up: shift items in [new_pos, old_pos) down by +1
        items = (
            db.query(Commitment)
            .filter(
                Commitment.status != CommitmentStatus.CLOSED,
                Commitment.priority_order.isnot(None),
                Commitment.priority_order >= new_pos,
                Commitment.priority_order < old_pos,
                Commitment.id != c.id,
            )
            .order_by(Commitment.priority_order.desc())
            .all()
        )
        for item in items:
            item.priority_order = item.priority_order + 1
    else:
        # Moving down: shift items in (old_pos, new_pos] up by -1
        items = (
            db.query(Commitment)
            .filter(
                Commitment.status != CommitmentStatus.CLOSED,
                Commitment.priority_order.isnot(None),
                Commitment.priority_order > old_pos,
                Commitment.priority_order <= new_pos,
                Commitment.id != c.id,
            )
            .order_by(Commitment.priority_order.asc())
            .all()
        )
        for item in items:
            item.priority_order = item.priority_order - 1

    c.priority_order = new_pos
    c.last_touched_at = datetime.now(timezone.utc)
    db.commit()
    _compact_priorities(db)
    db.commit()
    db.refresh(c)
    logger.info("Set commitment %s priority to %d", c.id, priority_order)
    return c


def list_open(db: Session) -> list[Commitment]:
    """Return all non-CLOSED commitments, oldest opened first."""
    return (
        db.query(Commitment)
        .filter(Commitment.status != CommitmentStatus.CLOSED)
        .order_by(Commitment.opened_at.asc())
        .all()
    )


def list_priorities(db: Session) -> list[Commitment]:
    """Return all non-CLOSED commitments that have a priority_order, sorted by rank."""
    return (
        db.query(Commitment)
        .filter(
            Commitment.status != CommitmentStatus.CLOSED,
            Commitment.priority_order.isnot(None),
        )
        .order_by(Commitment.priority_order.asc())
        .all()
    )


def get_dashboard(db: Session) -> dict:
    """Return all non-CLOSED commitments organized for display.

    Structure:
    1. priority_ranked: Items with a priority_order, sorted by rank (top priorities first)
    2. by_objective: Remaining items grouped by linked strategic objective
    3. ungrouped: Items with no priority and no linked objective, grouped by urgency

    Every non-CLOSED commitment appears exactly once.
    """
    all_open = (
        db.query(Commitment)
        .filter(Commitment.status != CommitmentStatus.CLOSED)
        .all()
    )

    # Split into priority-ranked vs rest
    priority_ranked = []
    rest = []
    for c in all_open:
        if c.priority_order is not None:
            priority_ranked.append(c)
        else:
            rest.append(c)

    priority_ranked.sort(key=lambda c: c.priority_order)

    # For the rest, check if they are linked to any active objectives
    rest_ids = {c.id for c in rest}

    # Get all objective links for the remaining commitments
    links = (
        db.query(ObjectiveCommitmentLink)
        .filter(ObjectiveCommitmentLink.commitment_id.in_(rest_ids))
        .all()
    ) if rest_ids else []

    # Build mapping: commitment_id -> list of objective_ids
    commit_to_objectives: dict[str, list] = {}
    objective_ids_needed: set = set()
    for link in links:
        cid = str(link.commitment_id)
        oid = str(link.objective_id)
        commit_to_objectives.setdefault(cid, []).append(oid)
        objective_ids_needed.add(link.objective_id)

    # Fetch objective details
    objectives_map: dict[str, StrategicObjective] = {}
    if objective_ids_needed:
        objs = (
            db.query(StrategicObjective)
            .filter(StrategicObjective.id.in_(objective_ids_needed))
            .all()
        )
        for o in objs:
            objectives_map[str(o.id)] = o

    # Group rest by objective (use first linked objective as primary grouping)
    by_objective: dict[str, list] = {}  # objective_id -> [commitments]
    ungrouped = []

    for c in rest:
        cid = str(c.id)
        if cid in commit_to_objectives:
            # Use the first linked objective as the grouping key
            primary_oid = commit_to_objectives[cid][0]
            by_objective.setdefault(primary_oid, []).append(c)
        else:
            ungrouped.append(c)

    # Build by_objective response with objective metadata
    by_objective_list = []
    for oid, commitments in by_objective.items():
        obj = objectives_map.get(oid)
        by_objective_list.append({
            "objective_id": oid,
            "objective_title": obj.title if obj else "Unknown",
            "objective_status": (obj.status.value if obj and hasattr(obj.status, "value") else str(obj.status)) if obj else "UNKNOWN",
            "commitments": commitments,
        })

    # Group ungrouped by urgency for logical display
    urgency_order = ["INCIDENT", "NOW", "SOON", "SCHEDULED", "SOMEDAY", "ADMIN", None]
    by_urgency: dict[str, list] = {}
    for c in ungrouped:
        u_key = c.urgency.value if c.urgency and hasattr(c.urgency, "value") else (c.urgency if c.urgency else "UNSET")
        by_urgency.setdefault(u_key, []).append(c)

    ungrouped_groups = []
    # Sort by urgency_order
    for u in urgency_order:
        key = u if u else "UNSET"
        if key in by_urgency:
            ungrouped_groups.append({
                "group_label": key,
                "commitments": by_urgency[key],
            })
    # Catch any urgency values not in the order list
    for key, commits in by_urgency.items():
        if key not in [u if u else "UNSET" for u in urgency_order]:
            ungrouped_groups.append({
                "group_label": key,
                "commitments": commits,
            })

    return {
        "total_open": len(all_open),
        "priority_ranked": priority_ranked,
        "by_objective": by_objective_list,
        "ungrouped": ungrouped_groups,
    }


# Urgency sort order (lower = higher priority)
_URGENCY_ORDER = {
    "INCIDENT": 0,
    "NOW": 1,
    "SOON": 2,
    "SCHEDULED": 3,
    "SOMEDAY": 4,
    "ADMIN": 5,
}

_PRIORITY_RE = re.compile(r"Priority\s+(\d+)\.", re.IGNORECASE)


def _urgency_rank(c: Commitment) -> int:
    """Return numeric sort rank for a commitment's urgency."""
    val = c.urgency.value if c.urgency and hasattr(c.urgency, "value") else (c.urgency or "")
    return _URGENCY_ORDER.get(val, 99)


def _person_str(c: Commitment) -> str:
    """Return person string or em-dash if missing."""
    return c.person if c.person else "\u2014"


def _due_str(c: Commitment) -> str:
    """Return formatted due date or em-dash if missing."""
    if c.due_at:
        return c.due_at.strftime("%b %-d")
    return "\u2014"


def _task_line_suffix(c: Commitment) -> str:
    """Return ' (person, due)' suffix for a task line."""
    return f" ({_person_str(c)}, {_due_str(c)})"


def _extract_priority_number(c: Commitment) -> int | None:
    """Extract priority number from description like 'Priority 1.' Returns None if none."""
    if c.description:
        m = _PRIORITY_RE.search(c.description)
        if m:
            return int(m.group(1))
    return None


def _sort_key(c: Commitment, priority_number: int = 0) -> tuple:
    """Multi-level sort key: priority number → urgency → due date → title."""
    if c.due_at:
        # Normalise to UTC-aware for comparison
        due_sort = c.due_at if c.due_at.tzinfo else c.due_at.replace(tzinfo=timezone.utc)
    else:
        due_sort = datetime(9999, 12, 31, tzinfo=timezone.utc)
    return (priority_number, _urgency_rank(c), due_sort, (c.title or "").lower())


def _blocked_suffix(c: Commitment, all_by_id: dict[str, Commitment]) -> str:
    """Return a blocked/depends suffix if the task has dependencies."""
    parts: list[str] = []
    if c.blocked_by_commitment_id:
        bid = str(c.blocked_by_commitment_id)
        blocker = all_by_id.get(bid)
        if blocker and blocker.status != CommitmentStatus.CLOSED:
            parts.append(f"BLOCKED by: {blocker.title}")
    if c.depends_on_commitment_id:
        did = str(c.depends_on_commitment_id)
        dep = all_by_id.get(did)
        if dep and dep.status != CommitmentStatus.CLOSED:
            parts.append(f"waiting on: {dep.title}")
    return f" [{'; '.join(parts)}]" if parts else ""


def _pipeline_status(c: Commitment) -> str:
    """Return pipeline position label if sequence_order is set."""
    if c.sequence_order is not None:
        return f" [Step {c.sequence_order}]"
    return ""


def format_dashboard_text(db: Session) -> str:
    """Return all non-CLOSED commitments as pre-formatted markdown text.

    The text is ready to display verbatim — no reformatting needed.

    Five sections (Leadership Execution Dashboard):
      1. Priority Execution — priority-ranked items (priority_order or "Priority N." description)
      2. Needs Decision — tasks with status WAITING or blocked
      3. Due Soon — tasks due within 7 days
      4. Initiatives — Theme > Initiative > Program > Tasks hierarchy
      5. Organization & Hiring — tasks with urgency ADMIN
    Remaining tasks go to Everything Else.
    Each task appears on a single line with (person, due date).
    """
    all_open = (
        db.query(Commitment)
        .filter(Commitment.status != CommitmentStatus.CLOSED)
        .all()
    )

    if not all_open:
        return "0 open tasks"

    all_by_id = {str(c.id): c for c in all_open}

    # Load active initiatives
    active_initiatives = (
        db.query(Initiative)
        .filter(Initiative.status == InitiativeStatus.ACTIVE)
        .order_by(Initiative.created_at.asc())
        .all()
    )
    init_map = {str(i.id): i for i in active_initiatives}

    # Load active programs
    active_programs = (
        db.query(Program)
        .filter(Program.status == ProgramStatus.ACTIVE)
        .order_by(Program.created_at.asc())
        .all()
    )
    prog_map = {str(p.id): p for p in active_programs}

    # Load themes for grouping
    from app.models import StrategicTheme, ThemeStatus
    active_themes = (
        db.query(StrategicTheme)
        .filter(StrategicTheme.status == ThemeStatus.ACTIVE)
        .order_by(StrategicTheme.created_at.asc())
        .all()
    )
    theme_map = {str(t.id): t for t in active_themes}

    # Categorise tasks into sections (a task appears in the first matching section)
    used_ids: set[str] = set()
    top_focus: list[Commitment] = []
    needs_decision: list[Commitment] = []
    due_soon: list[Commitment] = []
    org_hiring: list[Commitment] = []
    workstream_tasks: list[Commitment] = []
    everything_else: list[Commitment] = []

    now = datetime.now(timezone.utc)
    seven_days = now + timedelta(days=7)

    # Pass 1: Priority Execution — tasks with priority_order set OR "Priority N." in description
    priority_candidates: list[tuple[int, Commitment]] = []
    for c in all_open:
        if c.priority_order is not None:
            priority_candidates.append((c.priority_order, c))
        else:
            pnum = _extract_priority_number(c)
            if pnum is not None:
                priority_candidates.append((pnum, c))

    priority_candidates.sort(key=lambda x: x[0])
    for _, c in priority_candidates:
        top_focus.append(c)
        used_ids.add(str(c.id))

    # Pass 2: Needs Decision — WAITING status or blocked
    for c in all_open:
        cid = str(c.id)
        if cid in used_ids:
            continue
        is_waiting = c.status == CommitmentStatus.WAITING
        is_blocked = (
            c.blocked_by_commitment_id is not None
            and str(c.blocked_by_commitment_id) in all_by_id
            and all_by_id[str(c.blocked_by_commitment_id)].status != CommitmentStatus.CLOSED
        )
        if is_waiting or is_blocked:
            needs_decision.append(c)
            used_ids.add(cid)

    # Pass 3: Due Soon — due within 7 days
    for c in all_open:
        cid = str(c.id)
        if cid in used_ids:
            continue
        if c.due_at:
            due = c.due_at if c.due_at.tzinfo else c.due_at.replace(tzinfo=timezone.utc)
            if due <= seven_days:
                due_soon.append(c)
                used_ids.add(cid)

    # Pass 4: Organization & Hiring — urgency ADMIN
    for c in all_open:
        cid = str(c.id)
        if cid in used_ids:
            continue
        u_val = c.urgency.value if c.urgency and hasattr(c.urgency, "value") else c.urgency
        if u_val == "ADMIN":
            org_hiring.append(c)
            used_ids.add(cid)

    # Pass 5: Everything remaining goes to Initiatives/Workstreams or Everything Else
    for c in all_open:
        cid = str(c.id)
        if cid in used_ids:
            continue
        # If linked to an initiative (directly or via link table), it's a workstream task
        if c.initiative_id or c.program_id:
            workstream_tasks.append(c)
            used_ids.add(cid)

    # Also check InitiativeCommitmentLink for tasks not yet assigned
    remaining_ids = {str(c.id) for c in all_open if str(c.id) not in used_ids}
    if remaining_ids:
        links = (
            db.query(InitiativeCommitmentLink)
            .filter(InitiativeCommitmentLink.commitment_id.in_(
                [c.id for c in all_open if str(c.id) in remaining_ids]
            ))
            .all()
        )
        linked_ids = {str(link.commitment_id) for link in links}
        for c in all_open:
            cid = str(c.id)
            if cid in used_ids:
                continue
            if cid in linked_ids:
                workstream_tasks.append(c)
                used_ids.add(cid)
            else:
                everything_else.append(c)
                used_ids.add(cid)

    # Sort sections
    needs_decision.sort(key=lambda c: _sort_key(c))
    due_soon.sort(key=lambda c: (c.due_at or datetime(9999, 12, 31, tzinfo=timezone.utc), (c.title or "").lower()))
    org_hiring.sort(key=lambda c: _sort_key(c))
    everything_else.sort(key=lambda c: _sort_key(c))

    lines: list[str] = []

    # Section 1: Priority Execution
    if top_focus:
        lines.append("\U0001f3af Priority Execution")
        for i, c in enumerate(top_focus, 1):
            suffix = _blocked_suffix(c, all_by_id)
            lines.append(f"{i}. {c.title}{_task_line_suffix(c)}{suffix}")
        lines.append("")

    # Section 2: Needs Decision
    if needs_decision:
        lines.append("\u26a0\ufe0f Needs Decision")
        for c in needs_decision:
            suffix = _blocked_suffix(c, all_by_id)
            lines.append(f"\u2022 {c.title}{_task_line_suffix(c)}{suffix}")
        lines.append("")

    # Section 3: Due Soon
    if due_soon:
        lines.append("\U0001f525 Due Soon")
        for c in due_soon:
            lines.append(f"\u2022 {c.title}{_task_line_suffix(c)}")
        lines.append("")

    # Section 4: Initiatives — Theme > Initiative > Program > Tasks
    if workstream_tasks:
        lines.append("\U0001f6a7 Initiatives")

        # Build initiative -> commitment mapping
        init_prog_tasks: dict[str, dict[str, list[Commitment]]] = {}
        unassigned_workstream: list[Commitment] = []

        for c in workstream_tasks:
            iid = str(c.initiative_id) if c.initiative_id else None
            pid = str(c.program_id) if c.program_id else None

            if not iid:
                # Check link table
                link = (
                    db.query(InitiativeCommitmentLink)
                    .filter(InitiativeCommitmentLink.commitment_id == c.id)
                    .first()
                )
                if link:
                    iid = str(link.initiative_id)

            if iid:
                if iid not in init_prog_tasks:
                    init_prog_tasks[iid] = {}
                prog_key = pid or "_none"
                if prog_key not in init_prog_tasks[iid]:
                    init_prog_tasks[iid][prog_key] = []
                init_prog_tasks[iid][prog_key].append(c)
            else:
                unassigned_workstream.append(c)

        # Group initiatives by theme
        themed_inits: dict[str, list[str]] = {}  # theme_id -> [init_id, ...]
        unthemed_inits: list[str] = []

        for iid in init_prog_tasks:
            init_obj = init_map.get(iid)
            if init_obj and init_obj.theme_id and str(init_obj.theme_id) in theme_map:
                tid = str(init_obj.theme_id)
                if tid not in themed_inits:
                    themed_inits[tid] = []
                themed_inits[tid].append(iid)
            else:
                unthemed_inits.append(iid)

        def _render_initiative(iid: str, indent: int = 2) -> None:
            """Render an initiative and its programs/tasks."""
            init_obj = init_map.get(iid)
            init_title = init_obj.title if init_obj else "Unknown Initiative"
            init_owner = f" ({init_obj.owner})" if init_obj and init_obj.owner else ""
            lines.append(f"{' ' * indent}{init_title}{init_owner}")

            prog_groups = init_prog_tasks[iid]
            for prog_key, tasks in prog_groups.items():
                tasks.sort(key=lambda c: (c.sequence_order or 9999, _sort_key(c)))
                if prog_key != "_none":
                    prog_obj = prog_map.get(prog_key)
                    prog_title = prog_obj.title if prog_obj else "Unknown Program"
                    prog_owner = f" ({prog_obj.owner})" if prog_obj and prog_obj.owner else ""
                    lines.append(f"{' ' * (indent + 2)}{prog_title}{prog_owner}")
                    for c in tasks:
                        suffix = _blocked_suffix(c, all_by_id) + _pipeline_status(c)
                        lines.append(f"{' ' * (indent + 4)}\u2022 {c.title}{_task_line_suffix(c)}{suffix}")
                else:
                    for c in tasks:
                        suffix = _blocked_suffix(c, all_by_id) + _pipeline_status(c)
                        lines.append(f"{' ' * (indent + 2)}\u2022 {c.title}{_task_line_suffix(c)}{suffix}")

        # Render themed initiatives grouped under their theme
        for theme in active_themes:
            tid = str(theme.id)
            if tid in themed_inits:
                lines.append(f"  {theme.title}")
                for iid in themed_inits[tid]:
                    _render_initiative(iid, indent=4)

        # Render unthemed initiatives under "Other Initiatives"
        if unthemed_inits:
            lines.append("  Other Initiatives")
            for iid in unthemed_inits:
                _render_initiative(iid, indent=4)

        if unassigned_workstream:
            for c in unassigned_workstream:
                lines.append(f"  \u2022 {c.title}{_task_line_suffix(c)}")
        lines.append("")

    # Section 5: Organization & Hiring
    if org_hiring:
        lines.append("\U0001f331 Organization & Hiring")
        for c in org_hiring:
            lines.append(f"\u2022 {c.title}{_task_line_suffix(c)}")
        lines.append("")

    # Overflow: tasks that didn't fit any section
    if everything_else:
        lines.append("Everything Else")
        for c in everything_else:
            lines.append(f"\u2022 {c.title}{_task_line_suffix(c)}")
        lines.append("")

    return "\n".join(lines).strip()


def query_commitments(
    db: Session,
    *,
    person: Optional[str] = None,
    status: Optional[str] = None,
    urgency: Optional[str] = None,
    channel_type: Optional[str] = None,
    due_before: Optional[datetime] = None,
    due_after: Optional[datetime] = None,
    opened_before: Optional[datetime] = None,
    opened_after: Optional[datetime] = None,
    text: Optional[str] = None,
) -> list[Commitment]:
    """Flexible query with optional filters."""
    q = db.query(Commitment)

    if person:
        q = q.filter(Commitment.person.ilike(f"%{person}%"))
    if status:
        q = q.filter(Commitment.status == CommitmentStatus(status))
    if urgency:
        q = q.filter(Commitment.urgency == Urgency(urgency))
    if channel_type:
        q = q.filter(Commitment.channel_type == ChannelType(channel_type))
    if due_before:
        q = q.filter(Commitment.due_at <= due_before)
    if due_after:
        q = q.filter(Commitment.due_at >= due_after)
    if opened_before:
        q = q.filter(Commitment.opened_at <= opened_before)
    if opened_after:
        q = q.filter(Commitment.opened_at >= opened_after)
    if text:
        pattern = f"%{text}%"
        q = q.filter(
            or_(
                Commitment.title.ilike(pattern),
                Commitment.description.ilike(pattern),
            )
        )

    return q.order_by(Commitment.opened_at.asc()).all()
