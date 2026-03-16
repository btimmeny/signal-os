"""Strategic Signal System — Feature 021.

Every task open/close event generates a strategic signal that connects
execution to the platform strategy.  Signals feed into Friday updates
and Monday memos.
"""

from __future__ import annotations

import logging
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
    StrategicSignal,
    StrategicTheme,
    ThemeStatus,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# High-signal categories (patterns that represent meaningful progress)
# ---------------------------------------------------------------------------

_HIGH_SIGNAL_KEYWORDS = [
    "integration",
    "infrastructure",
    "platform",
    "capability",
    "pilot",
    "agent",
    "tooling",
    "release",
    "architecture",
    "pipeline",
    "deployment",
    "framework",
    "sdk",
    "api",
    "automation",
    "knowledge",
    "sdlc",
]

_SIGNAL_CATEGORIES = {
    "new_capability": ["capability", "feature", "release", "launch", "enable"],
    "infrastructure": ["infrastructure", "pipeline", "deployment", "architecture", "framework"],
    "tooling_integration": ["integration", "tooling", "sdk", "api", "cli", "plugin"],
    "pilot_progress": ["pilot", "poc", "prototype", "experiment", "trial"],
    "agent_capability": ["agent", "devin", "ai", "llm", "automation"],
    "knowledge_platform": ["knowledge", "documentation", "wiki", "index", "graph"],
}


# ---------------------------------------------------------------------------
# Signal generation helpers
# ---------------------------------------------------------------------------

def _get_commitment_context(db: Session, commitment: Commitment) -> dict:
    """Get initiative and theme context for a commitment."""
    # Find linked initiatives
    links = (
        db.query(InitiativeCommitmentLink)
        .filter(InitiativeCommitmentLink.commitment_id == commitment.id)
        .all()
    )

    initiative = None
    theme = None

    if links:
        # Use first linked initiative
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


def _classify_signal_category(title: str, description: str | None) -> str | None:
    """Determine the signal category based on task title and description."""
    text = (title + " " + (description or "")).lower()

    for category, keywords in _SIGNAL_CATEGORIES.items():
        for kw in keywords:
            if kw in text:
                return category
    return None


def _is_high_signal(title: str, description: str | None, has_initiative: bool) -> bool:
    """Determine if a task event represents a high-signal strategic event."""
    text = (title + " " + (description or "")).lower()

    # Tasks linked to initiatives are more likely high-signal
    if has_initiative:
        for kw in _HIGH_SIGNAL_KEYWORDS:
            if kw in text:
                return True

    # Even without initiative, strong strategic keywords qualify
    strong_keywords = ["infrastructure", "platform", "architecture", "capability", "release"]
    for kw in strong_keywords:
        if kw in text:
            return True

    return False


def _generate_contribution_note(
    commitment: Commitment,
    initiative: Initiative | None,
    theme: StrategicTheme | None,
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

    # No initiative or theme — still generate a note but flag it
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


def _generate_impact_note(
    commitment: Commitment,
    initiative: Initiative | None,
    theme: StrategicTheme | None,
) -> str:
    """Generate an Execution Impact Note for a closed task."""
    title = commitment.title

    if initiative and theme:
        return (
            f"Completing \"{title}\" advances the {initiative.title} initiative "
            f"within the {theme.title} strategic theme. "
            f"This closure represents measurable progress toward the platform "
            f"strategy and strengthens execution momentum."
        )

    if initiative:
        return (
            f"Completing \"{title}\" moves the {initiative.title} initiative forward. "
            f"This task closure contributes to execution velocity and demonstrates "
            f"progress within an active strategic workstream."
        )

    if theme:
        return (
            f"Completing \"{title}\" supports the {theme.title} strategic theme. "
            f"While not directly linked to an initiative, this closure contributes "
            f"to the broader strategic direction."
        )

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


# ---------------------------------------------------------------------------
# Core signal recording functions
# ---------------------------------------------------------------------------

def record_open_signal(db: Session, commitment: Commitment) -> StrategicSignal:
    """Record a strategic signal when a commitment is opened.

    - Determines initiative and theme context
    - Generates a Strategic Contribution Note
    - Stores the note on the commitment
    - Creates a StrategicSignal record
    """
    ctx = _get_commitment_context(db, commitment)
    initiative = ctx["initiative"]
    theme = ctx["theme"]

    # Generate contribution note
    note = _generate_contribution_note(commitment, initiative, theme)
    commitment.strategic_contribution_note = note

    # Classify signal
    has_initiative = initiative is not None
    high_signal = _is_high_signal(
        commitment.title, commitment.description, has_initiative
    )
    category = _classify_signal_category(commitment.title, commitment.description)

    signal = StrategicSignal(
        commitment_id=commitment.id,
        initiative_id=initiative.id if initiative else None,
        theme_id=theme.id if theme else None,
        event_type="OPENED",
        strategic_contribution=note,
        is_high_signal=1 if high_signal else 0,
        signal_category=category,
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)

    logger.info(
        "Recorded OPEN signal for commitment %s (initiative=%s, high_signal=%s)",
        commitment.id,
        initiative.title if initiative else "none",
        high_signal,
    )
    return signal


def record_close_signal(db: Session, commitment: Commitment) -> StrategicSignal:
    """Record a strategic signal when a commitment is closed.

    - Determines initiative and theme context
    - Generates an Execution Impact Note
    - Stores the note on the commitment
    - Creates a StrategicSignal record
    - Determines if this is a high-signal closure
    """
    ctx = _get_commitment_context(db, commitment)
    initiative = ctx["initiative"]
    theme = ctx["theme"]

    # Generate impact note
    note = _generate_impact_note(commitment, initiative, theme)
    commitment.execution_impact_note = note

    # Classify signal
    has_initiative = initiative is not None
    high_signal = _is_high_signal(
        commitment.title, commitment.description, has_initiative
    )
    category = _classify_signal_category(commitment.title, commitment.description)

    signal = StrategicSignal(
        commitment_id=commitment.id,
        initiative_id=initiative.id if initiative else None,
        theme_id=theme.id if theme else None,
        event_type="CLOSED",
        strategic_contribution=commitment.strategic_contribution_note,
        execution_impact=note,
        is_high_signal=1 if high_signal else 0,
        signal_category=category,
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)

    logger.info(
        "Recorded CLOSE signal for commitment %s (initiative=%s, high_signal=%s)",
        commitment.id,
        initiative.title if initiative else "none",
        high_signal,
    )
    return signal


# ---------------------------------------------------------------------------
# Signal queries
# ---------------------------------------------------------------------------

def get_signals_for_commitment(db: Session, commitment_id: str) -> list[StrategicSignal]:
    """Get all strategic signals for a specific commitment."""
    return (
        db.query(StrategicSignal)
        .filter(StrategicSignal.commitment_id == uuid.UUID(commitment_id))
        .order_by(StrategicSignal.created_at.desc())
        .all()
    )


def get_signals_for_period(
    db: Session,
    days_back: int = 7,
    now: datetime | None = None,
) -> list[StrategicSignal]:
    """Get all strategic signals from the past N days."""
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days_back)

    return (
        db.query(StrategicSignal)
        .filter(StrategicSignal.created_at >= cutoff)
        .order_by(StrategicSignal.created_at.desc())
        .all()
    )


def get_high_signal_closures(
    db: Session,
    days_back: int = 7,
    now: datetime | None = None,
) -> list[StrategicSignal]:
    """Get high-signal closure events from the past N days.

    These represent the most strategically meaningful task completions
    and should be prioritized in leadership narratives.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days_back)

    return (
        db.query(StrategicSignal)
        .filter(
            StrategicSignal.created_at >= cutoff,
            StrategicSignal.event_type == "CLOSED",
            StrategicSignal.is_high_signal == 1,
        )
        .order_by(StrategicSignal.created_at.desc())
        .all()
    )


def get_unclear_signals(
    db: Session,
    days_back: int = 7,
    now: datetime | None = None,
) -> list[StrategicSignal]:
    """Get signals where strategic contribution is unclear (no initiative link).

    These are candidates for Brian to clarify.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days_back)

    return (
        db.query(StrategicSignal)
        .filter(
            StrategicSignal.created_at >= cutoff,
            StrategicSignal.initiative_id.is_(None),
            StrategicSignal.theme_id.is_(None),
        )
        .order_by(StrategicSignal.created_at.desc())
        .all()
    )


def list_signals(
    db: Session,
    limit: int = 50,
    event_type: str | None = None,
    high_signal_only: bool = False,
) -> list[StrategicSignal]:
    """List recent strategic signals with optional filters."""
    q = db.query(StrategicSignal)

    if event_type:
        q = q.filter(StrategicSignal.event_type == event_type)
    if high_signal_only:
        q = q.filter(StrategicSignal.is_high_signal == 1)

    return q.order_by(StrategicSignal.created_at.desc()).limit(limit).all()


def get_signal(db: Session, signal_id: str) -> StrategicSignal | None:
    """Get a single strategic signal by ID."""
    return (
        db.query(StrategicSignal)
        .filter(StrategicSignal.id == uuid.UUID(signal_id))
        .first()
    )


# ---------------------------------------------------------------------------
# Weekly aggregation for Friday update / Monday memo
# ---------------------------------------------------------------------------

def aggregate_weekly_signals(
    db: Session,
    days_back: int = 7,
    now: datetime | None = None,
) -> dict:
    """Aggregate strategic signals for the week.

    Returns a structured summary for use in Friday updates and Monday memos:
    - high_signal_closures: list of high-impact completions
    - all_closures: all CLOSED signals
    - all_opens: all OPENED signals
    - unclear_signals: signals needing Brian's clarification
    - by_initiative: closures grouped by initiative
    - by_theme: closures grouped by theme
    - by_category: closures grouped by signal category
    - signal_count: total signals this period
    - high_signal_count: count of high-signal events
    """
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days_back)

    all_signals = (
        db.query(StrategicSignal)
        .filter(StrategicSignal.created_at >= cutoff)
        .order_by(StrategicSignal.created_at.desc())
        .all()
    )

    closures = [s for s in all_signals if s.event_type == "CLOSED"]
    opens = [s for s in all_signals if s.event_type == "OPENED"]
    high_closures = [s for s in closures if s.is_high_signal == 1]
    unclear = [s for s in all_signals if s.initiative_id is None and s.theme_id is None]

    # Group closures by initiative
    by_initiative: dict[str, list[StrategicSignal]] = {}
    for s in closures:
        if s.initiative_id:
            key = str(s.initiative_id)
            by_initiative.setdefault(key, []).append(s)

    # Group closures by theme
    by_theme: dict[str, list[StrategicSignal]] = {}
    for s in closures:
        if s.theme_id:
            key = str(s.theme_id)
            by_theme.setdefault(key, []).append(s)

    # Group closures by category
    by_category: dict[str, list[StrategicSignal]] = {}
    for s in closures:
        cat = s.signal_category or "uncategorized"
        by_category.setdefault(cat, []).append(s)

    # Resolve initiative and theme names
    initiative_names: dict[str, str] = {}
    for init_id in by_initiative:
        init = db.query(Initiative).filter(Initiative.id == uuid.UUID(init_id)).first()
        if init:
            initiative_names[init_id] = init.title

    theme_names: dict[str, str] = {}
    for theme_id in by_theme:
        theme = db.query(StrategicTheme).filter(StrategicTheme.id == uuid.UUID(theme_id)).first()
        if theme:
            theme_names[theme_id] = theme.title

    return {
        "high_signal_closures": high_closures,
        "all_closures": closures,
        "all_opens": opens,
        "unclear_signals": unclear,
        "by_initiative": by_initiative,
        "by_theme": by_theme,
        "by_category": by_category,
        "initiative_names": initiative_names,
        "theme_names": theme_names,
        "signal_count": len(all_signals),
        "high_signal_count": len(high_closures),
        "closure_count": len(closures),
        "open_count": len(opens),
    }


def format_signal_summary(aggregation: dict) -> str:
    """Format the weekly signal aggregation as a readable text summary.

    Used by Friday update and Monday memo to include strategic signal context.
    """
    lines = []
    high = aggregation["high_signal_closures"]
    closures = aggregation["all_closures"]
    opens = aggregation["all_opens"]
    unclear = aggregation["unclear_signals"]

    lines.append(f"Strategic Signals This Week: {aggregation['signal_count']} total "
                 f"({aggregation['closure_count']} closures, {aggregation['open_count']} opens)")

    if high:
        lines.append(f"\nHigh-Impact Completions ({len(high)}):")
        for s in high:
            commitment = s.commitment
            title = commitment.title if commitment else "Unknown"
            impact = s.execution_impact or "Impact not recorded"
            lines.append(f"  {title}")
            lines.append(f"    Impact: {impact}")

    if aggregation["by_initiative"]:
        lines.append(f"\nProgress by Initiative:")
        for init_id, signals in aggregation["by_initiative"].items():
            name = aggregation["initiative_names"].get(init_id, "Unknown")
            lines.append(f"  {name}: {len(signals)} task(s) completed")

    if aggregation["by_theme"]:
        lines.append(f"\nProgress by Strategic Theme:")
        for theme_id, signals in aggregation["by_theme"].items():
            name = aggregation["theme_names"].get(theme_id, "Unknown")
            lines.append(f"  {name}: {len(signals)} task(s) completed")

    if unclear:
        lines.append(f"\nSignals Needing Clarification ({len(unclear)}):")
        for s in unclear[:5]:  # Show at most 5
            commitment = s.commitment
            title = commitment.title if commitment else "Unknown"
            lines.append(f"  {title} ({s.event_type})")

    return "\n".join(lines)
