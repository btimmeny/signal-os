"""CRUD and generation logic for leadership memos.

Feature 019: Dynamic AI Platform Weekly Leadership Memo System.
All leadership roles, ownership, and organisational references are resolved
dynamically from the ``platform_leads`` table — nothing is hard-coded.

Memo sections follow a strict order:
  1. Strategic Objective
  2. Progress This Week
  3. Week Ahead
  4. Ownership & Execution
  5. Success Criteria

Content is rendered as short narrative paragraphs (3-5 sentences each,
no bullet lists).  Target length: 350-500 words.
"""

from __future__ import annotations

import io
import json
import logging
import os
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
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

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_STRATEGIC_OBJECTIVE = (
    "Our objective is to build the firm's AI-native development and knowledge "
    "platform enabling agents to build, review, and operate software using the "
    "firm's infrastructure, data, and knowledge fabric."
)

# Repo-relative paths for file persistence
_MEMO_DIR = Path("leadership-memos/ai-platform/weekly")
_EXPORT_DIR = _MEMO_DIR / "exports"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _week_start(dt: Optional[datetime] = None) -> datetime:
    """Return the Monday 00:00 UTC of the week containing *dt*."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    monday = dt - timedelta(days=dt.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def _parse_json_field(val: object, default: object = None) -> object:
    """Parse a JSON-encoded text field, returning *default* if not parseable."""
    if val is None:
        return default
    if isinstance(val, (list, dict)):
        return val
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return default


def _repo_root() -> Path:
    """Return the repository root directory."""
    root = os.environ.get("SIGNAL_OS_REPO_ROOT")
    if root:
        return Path(root)
    candidate = Path.cwd()
    if (candidate / "app").is_dir():
        return candidate
    return Path("/home/ubuntu/repos/signal-os")


def _active_leads(db: Session) -> list[PlatformLead]:
    """Return all active platform leads ordered by creation date."""
    return (
        db.query(PlatformLead)
        .filter(PlatformLead.active == 1)
        .order_by(PlatformLead.created_at.asc())
        .all()
    )


def _lead_initiative_ids(lead: PlatformLead) -> list[str]:
    """Parse the JSON initiative_ids on a lead, returning empty list on failure."""
    if not lead.initiative_ids:
        return []
    try:
        return json.loads(lead.initiative_ids)
    except (json.JSONDecodeError, TypeError):
        return []


# ---------------------------------------------------------------------------
# Narrative section builders
# ---------------------------------------------------------------------------


def _build_narrative_strategic_objective(
    db: Session,
    override: Optional[str] = None,
) -> str:
    """Return the strategic objective paragraph.

    Uses the override if provided, otherwise falls back to the most recent
    active strategic theme description or the built-in default.
    """
    if override:
        return override

    theme = (
        db.query(StrategicTheme)
        .filter(StrategicTheme.status == ThemeStatus.ACTIVE)
        .order_by(StrategicTheme.created_at.desc())
        .first()
    )
    if theme and theme.description:
        return theme.description

    return DEFAULT_STRATEGIC_OBJECTIVE


def _build_narrative_progress(db: Session, leads: list[PlatformLead]) -> str:
    """Build the *Progress This Week* narrative paragraph.

    Summarises recent activity across active initiatives and open commitments,
    attributing progress to the relevant platform leads.
    """
    active_initiatives = (
        db.query(Initiative)
        .filter(Initiative.status == InitiativeStatus.ACTIVE)
        .order_by(Initiative.created_at.asc())
        .all()
    )

    all_open = (
        db.query(Commitment)
        .filter(Commitment.status != CommitmentStatus.CLOSED)
        .all()
    )
    open_by_id = {str(c.id): c for c in all_open}

    init_titles: dict[str, str] = {}
    for init in active_initiatives:
        init_titles[str(init.id)] = init.title

    total_open = len(all_open)
    active_count = len(active_initiatives)

    snippets: list[str] = []
    for lead in leads:
        lead_init_ids = _lead_initiative_ids(lead)
        owned = [init_titles[iid] for iid in lead_init_ids if iid in init_titles]
        if owned:
            snippets.append(
                f"{lead.name} ({lead.role}) is driving {', '.join(owned[:2])}"
            )

    progress_text = (
        f"The platform team is tracking {total_open} open commitments across "
        f"{active_count} active initiatives this week. "
    )
    if snippets:
        progress_text += ". ".join(snippets[:3]) + ". "
    progress_text += (
        "The focus remains on converting planned work into measurable outcomes "
        "that advance the strategic objective."
    )
    return progress_text


def _build_narrative_week_ahead(db: Session) -> str:
    """Build the *Week Ahead* narrative paragraph.

    Highlights items due in the next seven days and top-priority commitments.
    """
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=7)

    due_soon = (
        db.query(Commitment)
        .filter(
            Commitment.status != CommitmentStatus.CLOSED,
            Commitment.due_at.isnot(None),
        )
        .all()
    )
    upcoming: list[str] = []
    for c in due_soon:
        due_at = c.due_at if c.due_at.tzinfo else c.due_at.replace(tzinfo=timezone.utc)
        if due_at <= cutoff:
            upcoming.append(c.title)

    top_priority = (
        db.query(Commitment)
        .filter(
            Commitment.status != CommitmentStatus.CLOSED,
            Commitment.priority_order.isnot(None),
        )
        .order_by(Commitment.priority_order.asc())
        .limit(3)
        .all()
    )
    priority_titles = [c.title for c in top_priority]

    parts: list[str] = []
    if upcoming:
        parts.append(
            f"In the coming week, {len(upcoming)} deliverable(s) approach their "
            f"target dates, including {', '.join(upcoming[:3])}"
        )
    if priority_titles:
        parts.append(
            f"Top-priority items requiring attention are {', '.join(priority_titles[:3])}"
        )
    if not parts:
        parts.append(
            "The week ahead is focused on sustaining momentum across all "
            "active workstreams and ensuring timely delivery of open commitments"
        )

    text = ". ".join(parts) + ". "
    text += (
        "Leadership should ensure blockers are surfaced early and that "
        "cross-functional dependencies are resolved before end of week."
    )
    return text


def _build_narrative_ownership(db: Session, leads: list[PlatformLead]) -> str:
    """Build the *Ownership & Execution* narrative paragraph.

    One sentence per active platform lead describing their execution focus.
    """
    if not leads:
        return (
            "Platform ownership is under review. Leadership roles will be "
            "confirmed and published once the organisational structure is finalised."
        )

    active_initiatives = (
        db.query(Initiative)
        .filter(Initiative.status == InitiativeStatus.ACTIVE)
        .all()
    )
    init_map = {str(i.id): i for i in active_initiatives}

    sentences: list[str] = []
    for lead in leads:
        init_ids = _lead_initiative_ids(lead)
        owned_titles = [init_map[iid].title for iid in init_ids if iid in init_map]
        if owned_titles:
            sentences.append(
                f"{lead.name}, {lead.role}, owns execution on "
                f"{', '.join(owned_titles[:2])} with a focus on {lead.focus_area}"
            )
        else:
            sentences.append(
                f"{lead.name}, {lead.role}, is focused on {lead.focus_area}"
            )

    text = ". ".join(sentences) + ". "
    text += (
        "Each lead is accountable for weekly progress against their assigned "
        "initiatives and is expected to flag risks early."
    )
    return text


def _build_narrative_success_criteria(db: Session) -> str:
    """Build the *Success Criteria* narrative paragraph.

    Derives criteria from active initiatives and top-priority commitments.
    """
    active_count = (
        db.query(Initiative)
        .filter(Initiative.status == InitiativeStatus.ACTIVE)
        .count()
    )

    top_priority = (
        db.query(Commitment)
        .filter(
            Commitment.status != CommitmentStatus.CLOSED,
            Commitment.priority_order.isnot(None),
        )
        .order_by(Commitment.priority_order.asc())
        .limit(3)
        .all()
    )
    priority_titles = [c.title for c in top_priority]

    text = (
        f"This week will be successful if progress is demonstrated across "
        f"all {active_count} active initiatives. "
    )
    if priority_titles:
        text += (
            f"Particular emphasis is on advancing {', '.join(priority_titles[:3])}. "
        )
    text += (
        "Outcomes should be measurable and each lead's contribution should "
        "clearly advance the strategic objective. The emphasis must be on "
        "outcomes rather than activity."
    )
    return text


# ---------------------------------------------------------------------------
# Dashboard snapshot (kept for backward compatibility with DB field)
# ---------------------------------------------------------------------------


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
        if c.priority_order is not None:
            top_focus.append(c.title)
        if c.due_at:
            due_at = c.due_at if c.due_at.tzinfo else c.due_at.replace(tzinfo=timezone.utc)
            if due_at <= due_soon_cutoff:
                due_soon.append(f"{c.title} (due {c.due_at.strftime('%b %-d')})")

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
        "needs_decision": [],
        "due_soon": due_soon,
        "active_workstreams": active_workstreams,
    }


def _build_lead_updates(db: Session) -> dict:
    """Group initiatives and tasks by platform lead (JSON stored in DB)."""
    leads = _active_leads(db)

    active_initiatives = (
        db.query(Initiative)
        .filter(Initiative.status == InitiativeStatus.ACTIVE)
        .all()
    )
    init_map = {str(i.id): i for i in active_initiatives}

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
        tasks = [open_by_id[str(lnk.commitment_id)].title
                 for lnk in links if str(lnk.commitment_id) in open_by_id]
        if tasks:
            init_tasks[str(init.id)] = tasks

    updates: dict[str, dict] = {}
    for lead in leads:
        lead_init_ids = _lead_initiative_ids(lead)

        progress: list[str] = []
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

        if not lead_init_ids:
            focus_keywords = [kw.strip().lower() for kw in lead.focus_area.split(",")]
            for init in active_initiatives:
                if any(kw in init.title.lower() for kw in focus_keywords):
                    tasks = init_tasks.get(str(init.id), [])
                    for t in tasks:
                        progress.append(f"{init.title}: {t}")

        updates[lead.name] = {
            "role": lead.role,
            "focus": lead.focus_area,
            "progress": progress,
            "next_focus": [],
        }

    return updates


# ---------------------------------------------------------------------------
# Memo generation
# ---------------------------------------------------------------------------


def generate_memo(
    db: Session,
    *,
    author: Optional[str] = None,
    strategic_objective: Optional[str] = None,
) -> LeadershipMemo:
    """Generate a weekly leadership memo from current data store state.

    All leadership roles are resolved dynamically from the platform_leads
    table.  Content is stored in the existing LeadershipMemo columns as
    JSON where needed.
    """
    leads = _active_leads(db)
    snapshot = _gather_dashboard_snapshot(db)
    lead_updates = _build_lead_updates(db)

    # Build narrative sections
    obj_text = _build_narrative_strategic_objective(db, override=strategic_objective)
    progress_text = _build_narrative_progress(db, leads)
    week_ahead_text = _build_narrative_week_ahead(db)
    ownership_text = _build_narrative_ownership(db, leads)
    criteria_text = _build_narrative_success_criteria(db)

    # Audience = all active leads
    audience = [ld.name for ld in leads] if leads else []

    memo = LeadershipMemo(
        id=uuid.uuid4(),
        week_start_date=_week_start(),
        author=author,
        status=MemoStatus.DRAFT,
        strategic_objective=obj_text,
        current_priorities=json.dumps([]),  # replaced by narrative progress
        progress_summary=progress_text,
        focus_next_week=json.dumps(week_ahead_text),
        success_criteria=json.dumps(criteria_text),
        lead_updates=json.dumps(lead_updates),
        dashboard_snapshot=json.dumps(snapshot),
        audience=json.dumps(audience),
    )
    db.add(memo)
    db.commit()
    db.refresh(memo)
    return memo


# ---------------------------------------------------------------------------
# Markdown formatting — narrative style
# ---------------------------------------------------------------------------


def format_memo_markdown(memo: LeadershipMemo) -> str:
    """Render a memo as a Markdown document using narrative paragraphs.

    Section order:
      1. Strategic Objective
      2. Progress This Week
      3. Week Ahead
      4. Ownership & Execution
      5. Success Criteria

    No bullet lists.  Target 350-500 words.
    """
    audience = _parse_json_field(memo.audience, [])
    lead_updates = _parse_json_field(memo.lead_updates, {})

    # Unpack narrative fields (stored as plain text or JSON strings)
    progress_text = memo.progress_summary or ""
    week_ahead_text = _parse_json_field(memo.focus_next_week, "")
    if isinstance(week_ahead_text, list):
        week_ahead_text = ", ".join(week_ahead_text)
    criteria_text = _parse_json_field(memo.success_criteria, "")
    if isinstance(criteria_text, list):
        criteria_text = ", ".join(criteria_text)

    # Build ownership paragraph from lead_updates
    ownership_sentences: list[str] = []
    for name, info in lead_updates.items():
        role = info.get("role", "")
        focus = info.get("focus", "")
        progress_items = info.get("progress", [])
        if progress_items:
            ownership_sentences.append(
                f"{name}, {role}, is advancing work on "
                f"{', '.join(progress_items[:2])} with a focus on {focus}"
            )
        else:
            ownership_sentences.append(
                f"{name}, {role}, is focused on {focus}"
            )
    ownership_text = ". ".join(ownership_sentences) + "." if ownership_sentences else ""
    if ownership_sentences:
        ownership_text += (
            " Each lead is accountable for weekly progress against their assigned "
            "initiatives and is expected to flag risks early."
        )

    date_str = memo.week_start_date.strftime("%B %-d, %Y")
    status_val = memo.status.value if hasattr(memo.status, "value") else memo.status

    lines: list[str] = [
        "# AI Platform Weekly Leadership Memo",
        "",
        f"**To:** {', '.join(audience) if audience else 'Leadership Team'}",
        f"**From:** {memo.author or 'Leadership'}",
        f"**Date:** {date_str}",
        f"**Status:** {status_val}",
        "",
        "## Strategic Objective",
        "",
        memo.strategic_objective or DEFAULT_STRATEGIC_OBJECTIVE,
        "",
        "## Progress This Week",
        "",
        progress_text,
        "",
        "## Week Ahead",
        "",
        week_ahead_text if isinstance(week_ahead_text, str) else str(week_ahead_text),
        "",
        "## Ownership & Execution",
        "",
        ownership_text,
        "",
        "## Success Criteria",
        "",
        criteria_text if isinstance(criteria_text, str) else str(criteria_text),
        "",
        "---",
        "",
        "*The emphasis should be on outcomes rather than activity.*",
    ]

    return "\n".join(lines)


def format_memo_text(db: Session, memo_id: str) -> Optional[str]:
    """Render a memo as formatted text (delegates to format_memo_markdown)."""
    memo = db.query(LeadershipMemo).filter(LeadershipMemo.id == uuid.UUID(memo_id)).first()
    if not memo:
        return None
    return format_memo_markdown(memo)


# ---------------------------------------------------------------------------
# File persistence
# ---------------------------------------------------------------------------


def _memo_filename(week_start: datetime) -> str:
    """Return the canonical filename for a weekly memo."""
    return f"ai-platform-weekly-memo-{week_start.strftime('%Y-%m-%d')}.md"


def _docx_filename(week_start: datetime) -> str:
    """Return the canonical .docx filename for a weekly memo."""
    return f"ai-platform-weekly-memo-{week_start.strftime('%Y-%m-%d')}.docx"


def save_memo_to_file(memo: LeadershipMemo, content: str) -> Path:
    """Save the Markdown memo to the repository file system.

    Creates ``/leadership-memos/ai-platform/weekly/<filename>.md``.
    Idempotent — overwrites if file already exists for that week.
    Returns the path to the written file.
    """
    root = _repo_root()
    memo_dir = root / _MEMO_DIR
    memo_dir.mkdir(parents=True, exist_ok=True)

    filepath = memo_dir / _memo_filename(memo.week_start_date)
    filepath.write_text(content, encoding="utf-8")
    log.info("Saved memo to %s", filepath)
    return filepath


# ---------------------------------------------------------------------------
# Pandoc conversion
# ---------------------------------------------------------------------------


def convert_memo_to_docx(md_path: Path) -> Optional[Path]:
    """Convert a Markdown memo to .docx via Pandoc.

    Saves the .docx into the ``exports/`` subdirectory.
    Returns the path to the created .docx or *None* on failure.
    """
    root = _repo_root()
    export_dir = root / _EXPORT_DIR
    export_dir.mkdir(parents=True, exist_ok=True)

    docx_name = md_path.stem + ".docx"
    docx_path = export_dir / docx_name

    try:
        result = subprocess.run(
            ["pandoc", str(md_path), "-o", str(docx_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            log.error("Pandoc conversion failed: %s", result.stderr)
            return None
        log.info("Converted memo to %s", docx_path)
        return docx_path
    except FileNotFoundError:
        log.warning("Pandoc not found — skipping .docx conversion")
        return None
    except subprocess.TimeoutExpired:
        log.error("Pandoc conversion timed out")
        return None


# ---------------------------------------------------------------------------
# Email distribution
# ---------------------------------------------------------------------------


def _build_recipient_list(db: Session) -> list[str]:
    """Return email addresses for all active platform leads.

    Only includes leads that have an email address set.
    """
    leads = _active_leads(db)
    emails: list[str] = []
    for lead in leads:
        if lead.email:
            emails.append(lead.email)
    return emails


def send_memo_email(
    db: Session,
    memo: LeadershipMemo,
    docx_path: Optional[Path] = None,
) -> bool:
    """Send the weekly memo via Gmail to the leadership team.

    Uses SMTP with an app password (env vars GMAIL_USER and GMAIL_APP_PASSWORD).
    Attaches the .docx file if available.  Returns True on success.
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders

    gmail_user = os.environ.get("GMAIL_USER")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_password:
        log.warning("Gmail credentials not configured — skipping email send")
        return False

    recipients = _build_recipient_list(db)
    if not recipients:
        log.warning("No recipients with email addresses — skipping email send")
        return False

    date_str = memo.week_start_date.strftime("%B %-d, %Y")
    subject = f"AI Platform Weekly Leadership Memo — {date_str}"

    md_content = format_memo_markdown(memo)

    msg = MIMEMultipart()
    msg["From"] = gmail_user
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    # Email body
    body = (
        f"Please find attached the AI Platform Weekly Leadership Memo for the "
        f"week of {date_str}.\n\n"
        f"This memo covers our strategic objective, progress this week, "
        f"the week ahead, ownership and execution updates, and success criteria.\n\n"
        f"Please review and reach out with any questions or feedback.\n\n"
        f"---\n\n{md_content}"
    )
    msg.attach(MIMEText(body, "plain"))

    # Attach .docx if available
    if docx_path and docx_path.exists():
        with open(docx_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={docx_path.name}",
            )
            msg.attach(part)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, recipients, msg.as_string())
        log.info("Memo email sent to %s", ", ".join(recipients))
        return True
    except Exception:
        log.exception("Failed to send memo email")
        return False


# ---------------------------------------------------------------------------
# Full workflow
# ---------------------------------------------------------------------------


def execute_memo_workflow(
    db: Session,
    *,
    author: Optional[str] = None,
    strategic_objective: Optional[str] = None,
    send_email: bool = True,
) -> dict:
    """Execute the full memo workflow: generate -> save -> convert -> email.

    Returns a dict with status information and file paths.
    """
    # 1. Get or generate memo for this week
    week_start = _week_start()
    existing = (
        db.query(LeadershipMemo)
        .filter(LeadershipMemo.week_start_date == week_start)
        .order_by(LeadershipMemo.created_at.desc())
        .first()
    )
    if existing:
        memo = existing
    else:
        memo = generate_memo(db, author=author, strategic_objective=strategic_objective)

    # 2. Format as Markdown
    md_content = format_memo_markdown(memo)

    # 3. Save to file
    md_path = save_memo_to_file(memo, md_content)

    # 4. Convert to .docx via Pandoc
    docx_path = convert_memo_to_docx(md_path)

    # 5. Send email
    email_sent = False
    if send_email:
        email_sent = send_memo_email(db, memo, docx_path)

    return {
        "memo_id": str(memo.id),
        "status": memo.status.value if hasattr(memo.status, "value") else memo.status,
        "md_path": str(md_path),
        "docx_path": str(docx_path) if docx_path else None,
        "email_sent": email_sent,
        "content": md_content,
    }


def get_or_generate_memo_text(db: Session, *, author: Optional[str] = None) -> str:
    """Get the latest memo for this week, or generate one. Return formatted text.

    Used by the /memo slash command.  Also triggers file persistence and
    conversion as a side-effect.
    """
    result = execute_memo_workflow(db, author=author, send_email=False)
    return result["content"]


# ---------------------------------------------------------------------------
# CRUD operations (unchanged public API)
# ---------------------------------------------------------------------------


def update_memo(
    db: Session,
    *,
    memo_id: str,
    **fields: object,
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


def export_memo_md(db: Session, memo_id: str) -> Optional[str]:
    """Export a memo as a markdown document. Returns None if not found."""
    memo = db.query(LeadershipMemo).filter(LeadershipMemo.id == uuid.UUID(memo_id)).first()
    if not memo:
        return None
    return format_memo_markdown(memo)


def export_memo_docx(db: Session, memo_id: str) -> Optional[bytes]:
    """Export a memo as a .docx Word document via Pandoc.

    Falls back to python-docx in-memory generation if Pandoc is not available.
    """
    memo = db.query(LeadershipMemo).filter(LeadershipMemo.id == uuid.UUID(memo_id)).first()
    if not memo:
        return None

    # Try Pandoc-based conversion first
    md_content = format_memo_markdown(memo)

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as tmp_md:
        tmp_md.write(md_content)
        tmp_md_path = Path(tmp_md.name)

    try:
        tmp_docx = tmp_md_path.with_suffix(".docx")
        result = subprocess.run(
            ["pandoc", str(tmp_md_path), "-o", str(tmp_docx)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and tmp_docx.exists():
            docx_bytes = tmp_docx.read_bytes()
            tmp_docx.unlink(missing_ok=True)
            tmp_md_path.unlink(missing_ok=True)
            return docx_bytes
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    finally:
        tmp_md_path.unlink(missing_ok=True)

    # Fallback: python-docx in-memory generation
    return _export_docx_fallback(memo)


def _export_docx_fallback(memo: LeadershipMemo) -> bytes:
    """Generate a .docx in-memory using python-docx as a fallback."""
    from docx import Document
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    audience = _parse_json_field(memo.audience, [])
    lead_updates = _parse_json_field(memo.lead_updates, {})

    doc = Document()
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Calibri"
    font.size = Pt(11)

    title_para = doc.add_heading("AI Platform Weekly Leadership Memo", level=0)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph(f"To: {', '.join(audience) if audience else 'Leadership Team'}")
    doc.add_paragraph(f"From: {memo.author or 'Leadership'}")
    doc.add_paragraph(f"Date: {memo.week_start_date.strftime('%B %-d, %Y')}")

    doc.add_heading("Strategic Objective", level=1)
    doc.add_paragraph(memo.strategic_objective or DEFAULT_STRATEGIC_OBJECTIVE)

    doc.add_heading("Progress This Week", level=1)
    doc.add_paragraph(memo.progress_summary or "")

    doc.add_heading("Week Ahead", level=1)
    week_ahead = _parse_json_field(memo.focus_next_week, "")
    doc.add_paragraph(week_ahead if isinstance(week_ahead, str) else str(week_ahead))

    doc.add_heading("Ownership & Execution", level=1)
    ownership_sentences: list[str] = []
    for name, info in lead_updates.items():
        role = info.get("role", "")
        focus = info.get("focus", "")
        ownership_sentences.append(f"{name}, {role}, is focused on {focus}")
    doc.add_paragraph(". ".join(ownership_sentences) + "." if ownership_sentences else "")

    doc.add_heading("Success Criteria", level=1)
    criteria = _parse_json_field(memo.success_criteria, "")
    doc.add_paragraph(criteria if isinstance(criteria, str) else str(criteria))

    footer = doc.add_paragraph("The emphasis should be on outcomes rather than activity.")
    footer.italic = True

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()
