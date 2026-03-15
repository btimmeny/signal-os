"""CRUD and generation logic for leadership memos."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    Commitment,
    CommitmentStatus,
    Initiative,
    InitiativeCommitmentLink,
    InitiativeStatus,
    LeadershipMemo,
    MemoStatus,
    PlatformLead,
    StrategicTheme,
    ThemeStatus,
)

# Default strategic objective text
DEFAULT_STRATEGIC_OBJECTIVE = (
    "Our objective is to build the firm's AI-native development and knowledge "
    "platform enabling agents to build, review, and operate software using the "
    "firm's infrastructure, data, and knowledge fabric."
)

# Default audience
DEFAULT_AUDIENCE = ["Matteo", "Mike", "Sterren", "Marina", "Deepak"]


def _week_start(dt: Optional[datetime] = None) -> datetime:
    """Return the Monday 00:00 UTC of the week containing *dt*."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    monday = dt - timedelta(days=dt.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def _gather_dashboard_snapshot(db: Session) -> dict:
    """Pull the current dashboard state for the memo snapshot."""
    all_open = (
        db.query(Commitment)
        .filter(Commitment.status != CommitmentStatus.CLOSED)
        .all()
    )

    now = datetime.now(timezone.utc)
    due_soon_cutoff = now + timedelta(days=7)

    top_focus: list[str] = []
    due_soon: list[str] = []
    active_workstreams: list[str] = []

    for c in all_open:
        # Top focus: items with priority_order
        if c.priority_order is not None:
            top_focus.append(c.title)

        # Due soon: items with due_at within next 7 days
        if c.due_at:
            due_at = c.due_at if c.due_at.tzinfo else c.due_at.replace(tzinfo=timezone.utc)
            if due_at <= due_soon_cutoff:
                due_soon.append(f"{c.title} (due {c.due_at.strftime('%b %-d')})")

    # Active workstreams: active initiatives
    active_initiatives = (
        db.query(Initiative)
        .filter(Initiative.status == InitiativeStatus.ACTIVE)
        .order_by(Initiative.created_at.asc())
        .all()
    )
    for init in active_initiatives:
        task_count = (
            db.query(InitiativeCommitmentLink)
            .join(Commitment, InitiativeCommitmentLink.commitment_id == Commitment.id)
            .filter(
                InitiativeCommitmentLink.initiative_id == init.id,
                Commitment.status != CommitmentStatus.CLOSED,
            )
            .count()
        )
        if task_count > 0:
            active_workstreams.append(f"{init.title} ({task_count} active tasks)")

    return {
        "top_focus": top_focus,
        "needs_decision": [],  # Placeholder for future use
        "due_soon": due_soon,
        "active_workstreams": active_workstreams,
    }


def _build_lead_updates(db: Session) -> dict:
    """Group initiatives and tasks by platform lead."""
    leads = (
        db.query(PlatformLead)
        .filter(PlatformLead.active == 1)
        .order_by(PlatformLead.created_at.asc())
        .all()
    )

    # Build mapping of initiative_id -> initiative
    active_initiatives = (
        db.query(Initiative)
        .filter(Initiative.status == InitiativeStatus.ACTIVE)
        .all()
    )
    init_map = {str(i.id): i for i in active_initiatives}

    # Build mapping of initiative_id -> open commitment titles
    all_open = (
        db.query(Commitment)
        .filter(Commitment.status != CommitmentStatus.CLOSED)
        .all()
    )
    open_by_id = {str(c.id): c for c in all_open}

    init_tasks: dict[str, list[str]] = {}
    for init in active_initiatives:
        links = (
            db.query(InitiativeCommitmentLink)
            .filter(InitiativeCommitmentLink.initiative_id == init.id)
            .all()
        )
        tasks = []
        for link in links:
            cid = str(link.commitment_id)
            if cid in open_by_id:
                tasks.append(open_by_id[cid].title)
        if tasks:
            init_tasks[str(init.id)] = tasks

    updates: dict[str, dict] = {}
    for lead in leads:
        lead_init_ids: list[str] = []
        if lead.initiative_ids:
            try:
                lead_init_ids = json.loads(lead.initiative_ids)
            except (json.JSONDecodeError, TypeError):
                lead_init_ids = []

        progress: list[str] = []
        next_focus: list[str] = []

        for iid in lead_init_ids:
            init = init_map.get(iid)
            if not init:
                continue
            tasks = init_tasks.get(iid, [])
            if tasks:
                for t in tasks:
                    progress.append(f"{init.title}: {t}")
            else:
                progress.append(f"{init.title}: No active tasks")

        # If no explicit initiative_ids, try matching by theme/focus_area
        if not lead_init_ids:
            # Match initiatives that contain the lead's focus_area keywords
            focus_keywords = [kw.strip().lower() for kw in lead.focus_area.split(",")]
            for init in active_initiatives:
                init_title_lower = init.title.lower()
                if any(kw in init_title_lower for kw in focus_keywords):
                    tasks = init_tasks.get(str(init.id), [])
                    if tasks:
                        for t in tasks:
                            progress.append(f"{init.title}: {t}")

        updates[lead.name] = {
            "role": lead.role,
            "focus": lead.focus_area,
            "progress": progress,
            "next_focus": next_focus,
        }

    return updates


def _build_priorities(db: Session) -> list[str]:
    """Extract current priorities from dashboard top focus items."""
    top = (
        db.query(Commitment)
        .filter(
            Commitment.status != CommitmentStatus.CLOSED,
            Commitment.priority_order.isnot(None),
        )
        .order_by(Commitment.priority_order.asc())
        .all()
    )
    return [c.title for c in top]


def _build_focus_next_week(snapshot: dict) -> list[str]:
    """Derive next week's focus from snapshot data."""
    items: list[str] = []
    for item in snapshot.get("due_soon", []):
        items.append(item)
    for item in snapshot.get("top_focus", []):
        if item not in items:
            items.append(item)
    return items[:5]  # Keep it concise


def _build_success_criteria(priorities: list[str]) -> list[str]:
    """Generate success criteria from priorities."""
    criteria: list[str] = []
    for i, p in enumerate(priorities[:3]):
        criteria.append(f"Achieve outcome aligned with: {p}")
    if not criteria:
        criteria.append("Maintain momentum across all active workstreams")
    return criteria


def generate_memo(
    db: Session,
    *,
    author: Optional[str] = None,
    strategic_objective: Optional[str] = None,
) -> LeadershipMemo:
    """Generate a weekly leadership memo from current dashboard state.

    Steps:
    1. Pull dashboard sections (top focus, due soon, active workstreams)
    2. Pull all active platform leads
    3. Group initiatives and tasks by platform lead
    4. Generate memo using template
    5. Save as draft
    """
    snapshot = _gather_dashboard_snapshot(db)
    lead_updates = _build_lead_updates(db)
    priorities = _build_priorities(db)
    focus_next = _build_focus_next_week(snapshot)
    criteria = _build_success_criteria(priorities)

    # Get audience from active leads
    leads = (
        db.query(PlatformLead)
        .filter(PlatformLead.active == 1)
        .order_by(PlatformLead.created_at.asc())
        .all()
    )
    audience = [l.name for l in leads] if leads else DEFAULT_AUDIENCE

    memo = LeadershipMemo(
        id=uuid.uuid4(),
        week_start_date=_week_start(),
        author=author,
        status=MemoStatus.DRAFT,
        strategic_objective=strategic_objective or DEFAULT_STRATEGIC_OBJECTIVE,
        current_priorities=json.dumps(priorities),
        progress_summary=f"{len(priorities)} priorities, {len(snapshot.get('active_workstreams', []))} active workstreams",
        focus_next_week=json.dumps(focus_next),
        success_criteria=json.dumps(criteria),
        lead_updates=json.dumps(lead_updates),
        dashboard_snapshot=json.dumps(snapshot),
        audience=json.dumps(audience),
    )
    db.add(memo)
    db.commit()
    db.refresh(memo)
    return memo


def format_memo_text(db: Session, memo_id: str) -> Optional[str]:
    """Render a memo as formatted markdown text."""
    memo = db.query(LeadershipMemo).filter(LeadershipMemo.id == uuid.UUID(memo_id)).first()
    if not memo:
        return None

    def _parse(val, default=None):
        if val is None:
            return default
        if isinstance(val, (list, dict)):
            return val
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return default

    audience = _parse(memo.audience, DEFAULT_AUDIENCE)
    priorities = _parse(memo.current_priorities, [])
    lead_updates = _parse(memo.lead_updates, {})
    focus_next = _parse(memo.focus_next_week, [])
    criteria = _parse(memo.success_criteria, [])

    lines: list[str] = []
    lines.append("AI Platform Weekly Leadership Memo")
    lines.append("")
    lines.append(f"To: {', '.join(audience)}")
    lines.append(f"From: {memo.author or 'Leadership'}")
    lines.append(f"Date: {memo.week_start_date.strftime('%B %-d, %Y')}")
    lines.append("")

    lines.append("Strategic Objective")
    lines.append("")
    lines.append(memo.strategic_objective or DEFAULT_STRATEGIC_OBJECTIVE)
    lines.append("")

    if priorities:
        lines.append("Current Priorities")
        lines.append("")
        for p in priorities:
            lines.append(f"• {p}")
        lines.append("")

    if lead_updates:
        lines.append("Platform Updates")
        lines.append("")
        for name, info in lead_updates.items():
            role = info.get("role", "")
            focus = info.get("focus", "")
            progress = info.get("progress", [])
            next_focus_items = info.get("next_focus", [])

            lines.append(f"{role} — {name}")
            lines.append(f"Focus: {focus}")
            lines.append("")
            lines.append("Progress")
            if progress:
                for item in progress:
                    lines.append(f"• {item}")
            else:
                lines.append("• No updates this week")
            lines.append("")
            lines.append("Next Focus")
            if next_focus_items:
                for item in next_focus_items:
                    lines.append(f"• {item}")
            else:
                lines.append("• Derived from priorities and due soon work")
            lines.append("")

    if focus_next:
        lines.append("Focus for Next Week")
        lines.append("")
        for item in focus_next:
            lines.append(f"• {item}")
        lines.append("")

    if criteria:
        lines.append("Success Criteria")
        lines.append("")
        lines.append("This week will be successful if we:")
        lines.append("")
        for item in criteria:
            lines.append(f"• {item}")
        lines.append("")

    lines.append("The emphasis should be on outcomes rather than activity.")

    return "\n".join(lines)


def update_memo(
    db: Session,
    *,
    memo_id: str,
    **fields,
) -> Optional[LeadershipMemo]:
    """Update a memo by ID. Returns None if not found."""
    memo = db.query(LeadershipMemo).filter(LeadershipMemo.id == uuid.UUID(memo_id)).first()
    if not memo:
        return None

    for k, v in fields.items():
        if v is not None:
            if k == "status":
                v = MemoStatus(v) if isinstance(v, str) else v
            elif k in ("current_priorities", "focus_next_week", "success_criteria", "audience"):
                v = json.dumps(v) if isinstance(v, list) else v
            elif k in ("lead_updates", "dashboard_snapshot"):
                v = json.dumps(v) if isinstance(v, dict) else v
            setattr(memo, k, v)

    db.commit()
    db.refresh(memo)
    return memo


def list_memos(
    db: Session,
    *,
    status: Optional[str] = None,
    limit: int = 20,
) -> list[LeadershipMemo]:
    """List memos, newest first, optionally filtered by status."""
    q = db.query(LeadershipMemo)
    if status:
        q = q.filter(LeadershipMemo.status == MemoStatus(status))
    return q.order_by(LeadershipMemo.created_at.desc()).limit(limit).all()


def get_memo(
    db: Session,
    *,
    memo_id: str,
) -> Optional[LeadershipMemo]:
    """Get a single memo by ID."""
    return db.query(LeadershipMemo).filter(LeadershipMemo.id == uuid.UUID(memo_id)).first()
