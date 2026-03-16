"""Strategic Execution Intelligence System — Feature 022.

Converts task activity into strategic insight and produces scheduled
weekly leadership updates.  All strategic commentary is persisted in
dedicated tables (durable strategic memory) so the system operates
independently of any single session.

Key responsibilities:
- Record StrategicContributionNotes on task open
- Record ExecutionImpactNotes on task close
- Populate StrategicNarrative, StrategyConfidenceHistory, WeeklyNarrative
  tables during Friday update generation
- Enforce idempotency (no duplicate signals / narratives on re-run)
- Support clarification prompts for unclear contributions
- Schedule Friday 12:00 PM auto-generation via APScheduler
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    Commitment,
    CommitmentStatus,
    ExecutionImpactNote,
    Initiative,
    InitiativeCommitmentLink,
    StrategicContributionNote,
    StrategicNarrative,
    StrategicSignal,
    StrategicTheme,
    StrategyConfidenceHistory,
    ThemeStatus,
    WeeklyNarrative,
    WeeklyStrategyUpdate,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default strategic objective
# ---------------------------------------------------------------------------

DEFAULT_STRATEGIC_OBJECTIVE = (
    "Build the AI-native platform that becomes the operational backbone "
    "of the business."
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _week_start(now: Optional[datetime] = None) -> datetime:
    """Return the Monday 00:00 UTC of the current week."""
    now = now or datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def _get_commitment_context(db: Session, commitment: Commitment) -> dict:
    """Get initiative and theme context for a commitment."""
    links = (
        db.query(InitiativeCommitmentLink)
        .filter(InitiativeCommitmentLink.commitment_id == commitment.id)
        .all()
    )

    initiative = None
    theme = None

    if links:
        init = db.query(Initiative).filter(Initiative.id == links[0].initiative_id).first()
        if init:
            initiative = init
            if init.theme_id:
                theme = db.query(StrategicTheme).filter(StrategicTheme.id == init.theme_id).first()

    return {
        "initiative": initiative,
        "theme": theme,
        "initiative_count": len(links),
    }


# ---------------------------------------------------------------------------
# SECTION 1 — Contribution Note (task open)
# ---------------------------------------------------------------------------


def _generate_contribution_text(
    commitment: Commitment,
    initiative: Optional[Initiative],
    theme: Optional[StrategicTheme],
) -> str:
    """Generate a Strategic Contribution Note for a newly opened task."""
    title = commitment.title

    if initiative and theme:
        return (
            f"This task contributes to the {initiative.title} initiative "
            f"under the {theme.title} strategic theme. "
            f"It advances the platform strategy by adding execution capacity "
            f"to an active workstream."
        )

    if initiative:
        return (
            f"This task supports the {initiative.title} initiative. "
            f"It adds to the execution agenda by contributing directly "
            f"to an active strategic workstream."
        )

    if theme:
        return (
            f"This task aligns with the {theme.title} strategic theme. "
            f"While not yet linked to a specific initiative, it contributes "
            f"to the broader strategic direction."
        )

    # No initiative or theme — unclear contribution
    from app.services.strategic_signals import _classify_signal_category

    category = _classify_signal_category(title, commitment.description)
    if category:
        cat_label = category.replace("_", " ")
        return (
            f"This task appears to relate to {cat_label}. "
            f"Its strategic contribution should be clarified by linking it "
            f"to an initiative or strategic theme."
        )

    return (
        f"This task was opened but its strategic contribution is unclear. "
        f"It should be linked to an initiative or strategic theme to ensure "
        f"it connects to the platform strategy."
    )


def record_contribution_note(
    db: Session,
    commitment: Commitment,
    *,
    now: Optional[datetime] = None,
) -> StrategicContributionNote:
    """Record a StrategicContributionNote when a task is opened.

    Idempotency: if a contribution note already exists for this task,
    return the existing record instead of creating a duplicate.
    """
    now = now or datetime.now(timezone.utc)

    # Check for existing note (idempotency)
    existing = (
        db.query(StrategicContributionNote)
        .filter(StrategicContributionNote.task_id == commitment.id)
        .first()
    )
    if existing:
        logger.info(
            "Contribution note already exists for commitment %s — skipping",
            commitment.id,
        )
        return existing

    ctx = _get_commitment_context(db, commitment)
    initiative = ctx["initiative"]
    theme = ctx["theme"]

    note_text = _generate_contribution_text(commitment, initiative, theme)

    # Determine source: "inferred" if no initiative/theme, else "inferred"
    # (user can later confirm via PATCH → source = "user_confirmed")
    source = "inferred"

    note = StrategicContributionNote(
        task_id=commitment.id,
        initiative_id=initiative.id if initiative else None,
        strategic_theme=theme.title if theme else None,
        strategic_contribution_note=note_text,
        source=source,
        created_at=now,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    logger.info(
        "Recorded contribution note for commitment %s (initiative=%s)",
        commitment.id,
        initiative.title if initiative else "none",
    )
    return note


def get_contribution_notes_for_task(
    db: Session, task_id: str
) -> list[StrategicContributionNote]:
    """Get all contribution notes for a specific task."""
    return (
        db.query(StrategicContributionNote)
        .filter(StrategicContributionNote.task_id == uuid.UUID(task_id))
        .order_by(StrategicContributionNote.created_at.desc())
        .all()
    )


def get_unclear_contributions(
    db: Session,
    days_back: int = 7,
    now: Optional[datetime] = None,
) -> list[StrategicContributionNote]:
    """Get contribution notes where the strategic contribution is unclear.

    These are candidates for Brian to clarify — notes without an initiative
    link whose source is still "inferred".
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days_back)

    return (
        db.query(StrategicContributionNote)
        .filter(
            StrategicContributionNote.created_at >= cutoff,
            StrategicContributionNote.initiative_id.is_(None),
            StrategicContributionNote.source == "inferred",
        )
        .order_by(StrategicContributionNote.created_at.desc())
        .all()
    )


def confirm_contribution_note(
    db: Session,
    note_id: str,
    *,
    updated_text: Optional[str] = None,
    initiative_id: Optional[str] = None,
    strategic_theme: Optional[str] = None,
) -> Optional[StrategicContributionNote]:
    """Confirm or update a contribution note (Brian's clarification).

    Sets source to "user_confirmed" and optionally updates the note text,
    initiative link, and strategic theme.
    """
    note = (
        db.query(StrategicContributionNote)
        .filter(StrategicContributionNote.id == uuid.UUID(note_id))
        .first()
    )
    if not note:
        return None

    note.source = "user_confirmed"
    if updated_text:
        note.strategic_contribution_note = updated_text
    if initiative_id:
        note.initiative_id = uuid.UUID(initiative_id)
    if strategic_theme:
        note.strategic_theme = strategic_theme

    db.commit()
    db.refresh(note)
    return note


# ---------------------------------------------------------------------------
# SECTION 2 — Impact Note (task close)
# ---------------------------------------------------------------------------


def _generate_impact_text(
    commitment: Commitment,
    initiative: Optional[Initiative],
    theme: Optional[StrategicTheme],
) -> str:
    """Generate an Execution Impact Note for a closed task."""
    title = commitment.title

    if initiative and theme:
        return (
            f'Completing "{title}" advances the {initiative.title} initiative '
            f"within the {theme.title} strategic theme. "
            f"This closure represents measurable progress toward the platform "
            f"strategy and strengthens execution momentum."
        )

    if initiative:
        return (
            f'Completing "{title}" moves the {initiative.title} initiative forward. '
            f"This task closure contributes to execution velocity and demonstrates "
            f"progress within an active strategic workstream."
        )

    if theme:
        return (
            f'Completing "{title}" supports the {theme.title} strategic theme. '
            f"While not directly linked to an initiative, this closure contributes "
            f"to the broader strategic direction."
        )

    from app.services.strategic_signals import _classify_signal_category

    category = _classify_signal_category(title, commitment.description)
    if category:
        cat_label = category.replace("_", " ")
        return (
            f"This task was closed. It appears to relate to {cat_label}. "
            f"Its strategic impact should be clarified to ensure the closure "
            f"is reflected in the execution narrative."
        )

    return (
        f"This task was closed but its strategic impact is unclear. "
        f"The completion should be reviewed to determine how it contributes "
        f"to the platform initiative."
    )


def _is_strategic_signal(
    title: str,
    description: Optional[str],
    has_initiative: bool,
) -> bool:
    """Determine if a task closure represents a strategic signal."""
    from app.services.strategic_signals import _is_high_signal

    return _is_high_signal(title, description, has_initiative)


def record_impact_note(
    db: Session,
    commitment: Commitment,
    *,
    now: Optional[datetime] = None,
) -> ExecutionImpactNote:
    """Record an ExecutionImpactNote when a task is closed.

    Idempotency: if an impact note already exists for this task,
    return the existing record instead of creating a duplicate.
    """
    now = now or datetime.now(timezone.utc)

    # Check for existing note (idempotency)
    existing = (
        db.query(ExecutionImpactNote)
        .filter(ExecutionImpactNote.task_id == commitment.id)
        .first()
    )
    if existing:
        logger.info(
            "Impact note already exists for commitment %s — skipping",
            commitment.id,
        )
        return existing

    ctx = _get_commitment_context(db, commitment)
    initiative = ctx["initiative"]
    theme = ctx["theme"]

    note_text = _generate_impact_text(commitment, initiative, theme)
    is_signal = _is_strategic_signal(
        commitment.title, commitment.description, initiative is not None
    )

    note = ExecutionImpactNote(
        task_id=commitment.id,
        initiative_id=initiative.id if initiative else None,
        execution_impact_note=note_text,
        strategic_signal_flag=1 if is_signal else 0,
        created_at=now,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    logger.info(
        "Recorded impact note for commitment %s (initiative=%s, signal=%s)",
        commitment.id,
        initiative.title if initiative else "none",
        is_signal,
    )
    return note


def get_impact_notes_for_task(
    db: Session, task_id: str
) -> list[ExecutionImpactNote]:
    """Get all impact notes for a specific task."""
    return (
        db.query(ExecutionImpactNote)
        .filter(ExecutionImpactNote.task_id == uuid.UUID(task_id))
        .order_by(ExecutionImpactNote.created_at.desc())
        .all()
    )


def get_high_signal_impact_notes(
    db: Session,
    days_back: int = 7,
    now: Optional[datetime] = None,
) -> list[ExecutionImpactNote]:
    """Get impact notes flagged as strategic signals for the period."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days_back)

    return (
        db.query(ExecutionImpactNote)
        .filter(
            ExecutionImpactNote.created_at >= cutoff,
            ExecutionImpactNote.strategic_signal_flag == 1,
        )
        .order_by(ExecutionImpactNote.created_at.desc())
        .all()
    )


# ---------------------------------------------------------------------------
# SECTION 3 — Strategic Narrative (week-over-week understanding)
# ---------------------------------------------------------------------------


def _build_strategic_narrative_record(
    db: Session,
    signals: dict,
    week_date: datetime,
) -> StrategicNarrative:
    """Build or update the StrategicNarrative record for a given week.

    Idempotency: updates existing record for the same week_date rather
    than creating duplicates.
    """
    # Identify momentum and friction signals
    closed = signals.get("commitments_closed", [])
    opened = signals.get("commitments_opened", [])
    overdue = signals.get("overdue", [])
    stalled = signals.get("stalled_initiatives", [])
    active_themes = signals.get("active_themes", [])
    active_inits = signals.get("active_initiatives", [])

    momentum = []
    if closed:
        momentum.append(f"{len(closed)} tasks completed this week")
    moving_inits = [
        i for i in active_inits if i.get("tasks_closed_this_week", 0) > 0
    ]
    if moving_inits:
        names = ", ".join(i["title"] for i in moving_inits[:3])
        momentum.append(f"Active execution in: {names}")
    if opened:
        momentum.append(f"{len(opened)} new tasks entered the pipeline")

    friction = []
    if overdue:
        momentum_titles = ", ".join(o["title"] for o in overdue[:3])
        friction.append(f"Overdue: {momentum_titles}")
    if stalled:
        stalled_titles = ", ".join(s["title"] for s in stalled[:3])
        friction.append(f"Stalled initiatives: {stalled_titles}")

    theme_names = [t["title"] for t in active_themes] if active_themes else []

    # Build narrative summary
    summary_parts = []
    if closed:
        summary_parts.append(
            f"The team closed {len(closed)} tasks this week, demonstrating "
            f"sustained execution against the platform strategy."
        )
    if moving_inits:
        summary_parts.append(
            f"{len(moving_inits)} of {len(active_inits)} initiatives showed "
            f"active task movement."
        )
    if stalled:
        summary_parts.append(
            f"{len(stalled)} initiatives showed no task movement and may "
            f"need attention."
        )
    narrative_summary = " ".join(summary_parts) if summary_parts else (
        "Limited execution data available for this period."
    )

    # Idempotency: check for existing record for this week
    existing = (
        db.query(StrategicNarrative)
        .filter(StrategicNarrative.date == week_date)
        .first()
    )

    if existing:
        # Update existing record
        existing.strategic_objective = DEFAULT_STRATEGIC_OBJECTIVE
        existing.strategic_themes = json.dumps(theme_names)
        existing.momentum_signals = json.dumps(momentum)
        existing.friction_signals = json.dumps(friction)
        existing.narrative_summary = narrative_summary
        db.commit()
        db.refresh(existing)
        logger.info("Updated existing StrategicNarrative for %s", week_date)
        return existing

    narrative = StrategicNarrative(
        date=week_date,
        strategic_objective=DEFAULT_STRATEGIC_OBJECTIVE,
        strategic_themes=json.dumps(theme_names),
        momentum_signals=json.dumps(momentum),
        friction_signals=json.dumps(friction),
        narrative_summary=narrative_summary,
        created_at=datetime.now(timezone.utc),
    )
    db.add(narrative)
    db.commit()
    db.refresh(narrative)
    logger.info("Created new StrategicNarrative for %s", week_date)
    return narrative


def get_strategic_narrative(
    db: Session,
    week_date: Optional[datetime] = None,
) -> Optional[StrategicNarrative]:
    """Get the StrategicNarrative for a given week."""
    if week_date is None:
        week_date = _week_start()
    return (
        db.query(StrategicNarrative)
        .filter(StrategicNarrative.date == week_date)
        .first()
    )


def list_strategic_narratives(
    db: Session,
    limit: int = 10,
) -> list[StrategicNarrative]:
    """List recent strategic narratives."""
    return (
        db.query(StrategicNarrative)
        .order_by(StrategicNarrative.date.desc())
        .limit(limit)
        .all()
    )


# ---------------------------------------------------------------------------
# SECTION 4 — Strategy Confidence History
# ---------------------------------------------------------------------------


def _record_confidence_history(
    db: Session,
    score: int,
    explanation: str,
    week_date: datetime,
) -> StrategyConfidenceHistory:
    """Record the Strategy Confidence Score for the week.

    Idempotency: updates existing record for the same week_date if the
    score has changed. Skips if score hasn't changed.
    """
    existing = (
        db.query(StrategyConfidenceHistory)
        .filter(StrategyConfidenceHistory.date == week_date)
        .first()
    )

    # Get previous week's score for trend
    prev_record = (
        db.query(StrategyConfidenceHistory)
        .filter(StrategyConfidenceHistory.date < week_date)
        .order_by(StrategyConfidenceHistory.date.desc())
        .first()
    )
    previous_score = prev_record.confidence_score if prev_record else None

    # Compute trend
    if previous_score is not None:
        diff = score - previous_score
        if diff >= 5:
            trend = "improving"
        elif diff <= -5:
            trend = "declining"
        else:
            trend = "flat"
    else:
        trend = "flat"

    if existing:
        # Only update if score has actually changed
        if existing.confidence_score == score:
            logger.info(
                "Confidence score unchanged for %s (%d) — skipping update",
                week_date,
                score,
            )
            return existing

        existing.confidence_score = score
        existing.previous_score = previous_score
        existing.trend_direction = trend
        existing.confidence_explanation = explanation
        db.commit()
        db.refresh(existing)
        logger.info("Updated confidence history for %s: %d", week_date, score)
        return existing

    record = StrategyConfidenceHistory(
        date=week_date,
        confidence_score=score,
        previous_score=previous_score,
        trend_direction=trend,
        confidence_explanation=explanation,
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info("Created confidence history for %s: %d (%s)", week_date, score, trend)
    return record


def get_confidence_history(
    db: Session,
    limit: int = 12,
) -> list[StrategyConfidenceHistory]:
    """Get recent confidence history records."""
    return (
        db.query(StrategyConfidenceHistory)
        .order_by(StrategyConfidenceHistory.date.desc())
        .limit(limit)
        .all()
    )


def get_latest_confidence(
    db: Session,
) -> Optional[StrategyConfidenceHistory]:
    """Get the most recent confidence record."""
    return (
        db.query(StrategyConfidenceHistory)
        .order_by(StrategyConfidenceHistory.date.desc())
        .first()
    )


# ---------------------------------------------------------------------------
# SECTION 5 — Weekly Narratives (3 drafts per week)
# ---------------------------------------------------------------------------


def _record_weekly_narratives(
    db: Session,
    narratives: list[dict],
    recommended_idx: int,
    week_date: datetime,
) -> list[WeeklyNarrative]:
    """Persist the three narrative drafts as WeeklyNarrative records.

    Idempotency: if narratives already exist for this week_date, update
    them rather than creating duplicates.
    """
    narrative_types = ["execution_progress", "momentum", "alignment"]
    results = []

    for idx, narrative in enumerate(narratives):
        ntype = narrative_types[idx] if idx < len(narrative_types) else f"option_{idx}"
        is_recommended = 1 if idx == recommended_idx else 0

        existing = (
            db.query(WeeklyNarrative)
            .filter(
                WeeklyNarrative.week_date == week_date,
                WeeklyNarrative.narrative_type == ntype,
            )
            .first()
        )

        if existing:
            existing.strategic_objective = narrative.get("strategic_objective", "")
            existing.narrative_text = narrative.get("body", "")
            existing.recommended_flag = is_recommended
            db.commit()
            db.refresh(existing)
            results.append(existing)
            logger.info("Updated weekly narrative %s for %s", ntype, week_date)
        else:
            wn = WeeklyNarrative(
                week_date=week_date,
                narrative_type=ntype,
                strategic_objective=narrative.get("strategic_objective", ""),
                narrative_text=narrative.get("body", ""),
                recommended_flag=is_recommended,
                created_at=datetime.now(timezone.utc),
            )
            db.add(wn)
            db.commit()
            db.refresh(wn)
            results.append(wn)
            logger.info("Created weekly narrative %s for %s", ntype, week_date)

    return results


def get_weekly_narratives(
    db: Session,
    week_date: Optional[datetime] = None,
) -> list[WeeklyNarrative]:
    """Get all narrative drafts for a given week."""
    if week_date is None:
        week_date = _week_start()
    return (
        db.query(WeeklyNarrative)
        .filter(WeeklyNarrative.week_date == week_date)
        .order_by(WeeklyNarrative.narrative_type)
        .all()
    )


def get_recommended_narrative(
    db: Session,
    week_date: Optional[datetime] = None,
) -> Optional[WeeklyNarrative]:
    """Get the recommended narrative for a given week."""
    if week_date is None:
        week_date = _week_start()
    return (
        db.query(WeeklyNarrative)
        .filter(
            WeeklyNarrative.week_date == week_date,
            WeeklyNarrative.recommended_flag == 1,
        )
        .first()
    )


# ---------------------------------------------------------------------------
# SECTION 6 — Integrated Friday Update Pipeline (Feature 022 extension)
# ---------------------------------------------------------------------------


def generate_intelligence_update(
    db: Session,
    *,
    send_email: bool = True,
    now: Optional[datetime] = None,
) -> dict:
    """Generate the complete Strategic Execution Intelligence update.

    This extends the Feature 020 Friday update by also persisting data
    into the Feature 022 dedicated tables:
    - StrategicNarrative (week-over-week understanding)
    - StrategyConfidenceHistory (trend tracking)
    - WeeklyNarrative (individual narrative drafts)

    Pipeline:
    1. Generate the base Friday update (Feature 020)
    2. Populate StrategicNarrative record
    3. Populate StrategyConfidenceHistory record
    4. Populate WeeklyNarrative records (3 drafts)

    All steps are idempotent — running multiple times for the same week
    will update existing records rather than creating duplicates.

    Returns a dict with the update record and all intelligence records.
    """
    from app.services.friday_update import generate_friday_update, extract_signals

    now = now or datetime.now(timezone.utc)
    week_date = _week_start(now)

    # Step 1: Generate the base Friday update
    update = generate_friday_update(db, send_email=send_email)

    # Step 2: Extract signals for StrategicNarrative
    signals = extract_signals(db, now=now)

    # Step 3: Populate StrategicNarrative
    narrative_record = _build_strategic_narrative_record(db, signals, week_date)

    # Step 4: Populate StrategyConfidenceHistory
    confidence_record = _record_confidence_history(
        db,
        score=update.confidence_score or 0,
        explanation=update.confidence_explanation or "",
        week_date=week_date,
    )

    # Step 5: Populate WeeklyNarrative records
    narratives_json = json.loads(update.narrative_options) if update.narrative_options else []
    weekly_narratives = _record_weekly_narratives(
        db,
        narratives_json,
        recommended_idx=update.recommended_narrative or 0,
        week_date=week_date,
    )

    logger.info(
        "Strategic intelligence update complete for %s: "
        "confidence=%d trend=%s narratives=%d",
        week_date,
        confidence_record.confidence_score,
        confidence_record.trend_direction,
        len(weekly_narratives),
    )

    return {
        "update": update,
        "strategic_narrative": narrative_record,
        "confidence_history": confidence_record,
        "weekly_narratives": weekly_narratives,
    }


# ---------------------------------------------------------------------------
# SECTION 7 — Confidence Score Band Labels
# ---------------------------------------------------------------------------


def confidence_band_label(score: int) -> str:
    """Return the human-readable band label for a confidence score.

    0-30:  Struggling — strategy execution not translating
    30-60: Mixed — some signals but gaps remain
    60-80: Strong — strategy clearly executing
    80-100: Clearly Working — strong signal across all dimensions
    """
    if score < 30:
        return "Struggling — strategy execution not translating"
    if score < 60:
        return "Mixed — some signals but gaps remain"
    if score < 80:
        return "Strong — strategy clearly executing"
    return "Clearly Working — strong signal across all dimensions"


# ---------------------------------------------------------------------------
# SECTION 8 — Email Output (Feature 022 format)
# ---------------------------------------------------------------------------


def compose_intelligence_email(
    update: WeeklyStrategyUpdate,
    confidence_history: StrategyConfidenceHistory,
    weekly_narratives: list[WeeklyNarrative],
    strategic_narrative: StrategicNarrative,
) -> str:
    """Compose the Feature 022 email with all sections.

    Subject: AI Platform Weekly Status Draft — Strategic Update
    Structure:
    1. Three narrative options with strategic explanations
    2. Recommended narrative
    3. Strategic continuity analysis
    4. Strategy Confidence Signal with trend
    5. Forwardable version
    """
    narratives_json = json.loads(update.narrative_options) if update.narrative_options else []
    score_components = json.loads(update.score_components) if update.score_components else {}
    date_str = update.week_start_date.strftime("%B %-d, %Y")

    lines = []

    # Greeting
    lines.append("Brian,")
    lines.append("")
    lines.append(
        f"Here is your AI Platform Weekly Status Draft — Strategic Update "
        f"for the week of {date_str}. Below you'll find three narrative "
        f"options, a recommended selection, strategic continuity analysis, "
        f"and your Strategy Confidence Signal."
    )
    lines.append("")

    # Three Narrative Options
    for idx, narrative in enumerate(narratives_json):
        option_num = idx + 1
        lines.append(
            f"--- NARRATIVE OPTION {option_num}: "
            f"{narrative['framing'].upper()} ---"
        )
        lines.append("")
        lines.append(f"Strategic Objective: {narrative['strategic_objective']}")
        lines.append(f"Why This Framing Works: {narrative['why']}")
        lines.append(f"Behavior It Drives: {narrative['behavior']}")
        lines.append("")
        lines.append(narrative["body"])
        lines.append("")

    # Recommended Narrative
    rec_idx = update.recommended_narrative or 0
    rec_name = (
        narratives_json[rec_idx]["framing"]
        if rec_idx < len(narratives_json)
        else "Execution Progress"
    )
    lines.append("--- RECOMMENDED NARRATIVE ---")
    lines.append("")
    lines.append(f"Recommended: Option {rec_idx + 1} ({rec_name})")
    lines.append("")

    # Strategic Continuity Analysis
    lines.append("--- STRATEGIC CONTINUITY ANALYSIS ---")
    lines.append("")
    if strategic_narrative and strategic_narrative.narrative_summary:
        lines.append(strategic_narrative.narrative_summary)
    else:
        lines.append(update.narrative_continuity or "")
    lines.append("")

    # Strategy Confidence Signal
    trend_labels = {
        "improving": "(improving)",
        "declining": "(declining)",
        "flat": "(flat)",
        "up": "(improving)",
        "down": "(declining)",
        "stable": "(flat)",
    }
    trend_label = trend_labels.get(
        confidence_history.trend_direction or "flat", "(flat)"
    )
    band = confidence_band_label(confidence_history.confidence_score)

    lines.append("--- STRATEGY CONFIDENCE SIGNAL ---")
    lines.append("")
    lines.append(
        f"Score: {confidence_history.confidence_score}/100 {trend_label}"
    )
    lines.append(f"Band: {band}")
    if confidence_history.previous_score is not None:
        lines.append(
            f"Previous: {confidence_history.previous_score}/100"
        )
    if score_components:
        lines.append(
            f"  Execution: {score_components.get('execution', 'N/A')}/100"
        )
        lines.append(
            f"  Momentum: {score_components.get('momentum', 'N/A')}/100"
        )
        lines.append(
            f"  Alignment: {score_components.get('alignment', 'N/A')}/100"
        )
        lines.append(
            f"  Friction (inverted): {score_components.get('friction', 'N/A')}/100"
        )
    lines.append(
        f"Explanation: {confidence_history.confidence_explanation or 'N/A'}"
    )
    lines.append("")

    # Forwardable Version
    lines.append(
        "--- FORWARDABLE VERSION (copy below to forward to the team) ---"
    )
    lines.append("")
    lines.append(update.forwardable_body or "")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# SECTION 9 — Scheduler (Friday 12:00 PM)
# ---------------------------------------------------------------------------


def setup_scheduler(get_db_session_func):
    """Configure APScheduler to run the intelligence update every Friday at 12:00 PM.

    Parameters:
        get_db_session_func: a callable that returns a SQLAlchemy Session
                             (typically the FastAPI get_db dependency).

    Returns the scheduler instance so it can be shut down on app exit.
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning(
            "APScheduler not installed — Friday scheduled updates will not run. "
            "Install with: pip install apscheduler"
        )
        return None

    def _run_scheduled_update():
        """Callback executed by APScheduler every Friday at noon."""
        logger.info("Scheduled Friday intelligence update starting...")
        db = next(get_db_session_func())
        try:
            result = generate_intelligence_update(db, send_email=True)
            logger.info(
                "Scheduled update complete — confidence=%d",
                result["confidence_history"].confidence_score,
            )
        except Exception:
            logger.exception("Scheduled Friday intelligence update failed")
        finally:
            db.close()

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _run_scheduled_update,
        CronTrigger(day_of_week="fri", hour=12, minute=0, timezone="UTC"),
        id="friday_intelligence_update",
        name="Friday Strategic Execution Intelligence Update",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler started — Friday updates scheduled for 12:00 PM UTC")
    return scheduler


# ---------------------------------------------------------------------------
# SECTION 10 — List / Query helpers
# ---------------------------------------------------------------------------


def list_contribution_notes(
    db: Session,
    limit: int = 50,
    days_back: Optional[int] = None,
    now: Optional[datetime] = None,
) -> list[StrategicContributionNote]:
    """List recent contribution notes."""
    q = db.query(StrategicContributionNote)
    if days_back is not None:
        now = now or datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days_back)
        q = q.filter(StrategicContributionNote.created_at >= cutoff)
    return q.order_by(StrategicContributionNote.created_at.desc()).limit(limit).all()


def list_impact_notes(
    db: Session,
    limit: int = 50,
    days_back: Optional[int] = None,
    now: Optional[datetime] = None,
) -> list[ExecutionImpactNote]:
    """List recent impact notes."""
    q = db.query(ExecutionImpactNote)
    if days_back is not None:
        now = now or datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days_back)
        q = q.filter(ExecutionImpactNote.created_at >= cutoff)
    return q.order_by(ExecutionImpactNote.created_at.desc()).limit(limit).all()
