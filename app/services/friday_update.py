"""Friday Strategic Execution Update — Feature 020.

Generates a weekly strategic execution update every Friday with:
- Signal extraction from the past 7 days
- Three narrative drafts with different strategic framings
- Strategy Confidence Score (0-100) with trend
- Week-over-week comparison
- Forwardable email for Brian to send to the team
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    Commitment,
    CommitmentComment,
    CommitmentStatus,
    Initiative,
    InitiativeCommitmentLink,
    InitiativeStatus,
    StrategicObjective,
    StrategicTheme,
    ThemeStatus,
    UpdateStatus,
    WeeklyStrategyUpdate,
)

log = logging.getLogger(__name__)

# Default strategic objective (matches memo system)
DEFAULT_STRATEGIC_OBJECTIVE = (
    "Build the AI-native platform that becomes the operational backbone of the business."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _week_start(now: Optional[datetime] = None) -> datetime:
    """Return the Monday 00:00 UTC of the current week."""
    now = now or datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def _seven_days_ago(now: Optional[datetime] = None) -> datetime:
    """Return datetime 7 days before now."""
    now = now or datetime.now(timezone.utc)
    return now - timedelta(days=7)


# ---------------------------------------------------------------------------
# Signal Extraction
# ---------------------------------------------------------------------------

def extract_signals(db: Session, now: Optional[datetime] = None) -> dict:
    """Extract meaningful execution signals from the past 7 days.

    Returns a dict with keys:
        - commitments_closed: tasks closed in the past 7 days
        - commitments_opened: tasks opened in the past 7 days
        - total_open: total open tasks right now
        - overdue: tasks past their due date
        - due_soon: tasks due in the next 7 days
        - active_initiatives: initiatives with ACTIVE status
        - completed_initiatives: initiatives completed in the period
        - stalled_initiatives: active initiatives with no recent task movement
        - active_themes: strategic themes that are ACTIVE
        - recent_comments: comments added in the past 7 days
        - priorities: tasks with priority_order set
    """
    now = now or datetime.now(timezone.utc)
    cutoff = _seven_days_ago(now)
    week_ahead = now + timedelta(days=7)

    # --- Commitments ---
    all_commitments = db.query(Commitment).all()

    commitments_closed = []
    commitments_opened = []
    total_open = []
    overdue = []
    due_soon = []
    priorities = []

    for c in all_commitments:
        opened_at = c.opened_at
        if opened_at and opened_at.tzinfo is None:
            opened_at = opened_at.replace(tzinfo=timezone.utc)

        closed_at = c.closed_at
        if closed_at and closed_at.tzinfo is None:
            closed_at = closed_at.replace(tzinfo=timezone.utc)

        due_at = c.due_at
        if due_at and due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=timezone.utc)

        status_val = c.status.value if hasattr(c.status, "value") else c.status

        if status_val == "CLOSED":
            if closed_at and closed_at >= cutoff:
                commitments_closed.append({
                    "id": str(c.id),
                    "title": c.title,
                    "closed_at": closed_at.isoformat(),
                })
        else:
            total_open.append({
                "id": str(c.id),
                "title": c.title,
                "status": status_val,
                "urgency": (c.urgency.value if c.urgency and hasattr(c.urgency, "value") else c.urgency),
            })

            if due_at:
                if due_at < now:
                    overdue.append({
                        "id": str(c.id),
                        "title": c.title,
                        "due_at": due_at.isoformat(),
                    })
                elif due_at <= week_ahead:
                    due_soon.append({
                        "id": str(c.id),
                        "title": c.title,
                        "due_at": due_at.isoformat(),
                    })

            if c.priority_order is not None:
                priorities.append({
                    "id": str(c.id),
                    "title": c.title,
                    "priority_order": c.priority_order,
                })

        if opened_at and opened_at >= cutoff and status_val != "CLOSED":
            commitments_opened.append({
                "id": str(c.id),
                "title": c.title,
                "opened_at": opened_at.isoformat(),
            })

    priorities.sort(key=lambda x: x["priority_order"])

    # --- Initiatives ---
    all_initiatives = db.query(Initiative).all()
    active_initiatives = []
    completed_initiatives = []
    stalled_initiatives = []

    for init in all_initiatives:
        status_val = init.status.value if hasattr(init.status, "value") else init.status
        if status_val == "ACTIVE":
            # Count active tasks for this initiative
            task_count = (
                db.query(InitiativeCommitmentLink)
                .join(Commitment, InitiativeCommitmentLink.commitment_id == Commitment.id)
                .filter(
                    InitiativeCommitmentLink.initiative_id == init.id,
                    Commitment.status != CommitmentStatus.CLOSED,
                )
                .count()
            )
            # Count tasks closed in the past 7 days for this initiative
            closed_count = (
                db.query(InitiativeCommitmentLink)
                .join(Commitment, InitiativeCommitmentLink.commitment_id == Commitment.id)
                .filter(
                    InitiativeCommitmentLink.initiative_id == init.id,
                    Commitment.status == CommitmentStatus.CLOSED,
                    Commitment.closed_at >= cutoff,
                )
                .count()
            )
            info = {
                "id": str(init.id),
                "title": init.title,
                "active_tasks": task_count,
                "tasks_closed_this_week": closed_count,
            }
            active_initiatives.append(info)
            if task_count > 0 and closed_count == 0:
                stalled_initiatives.append(info)
        elif status_val == "COMPLETED":
            updated_at = init.updated_at
            if updated_at and updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            if updated_at and updated_at >= cutoff:
                completed_initiatives.append({
                    "id": str(init.id),
                    "title": init.title,
                })

    # --- Strategic Themes ---
    active_themes = []
    for theme in db.query(StrategicTheme).filter(StrategicTheme.status == ThemeStatus.ACTIVE).all():
        active_themes.append({
            "id": str(theme.id),
            "title": theme.title,
        })

    # --- Recent comments ---
    recent_comments = []
    for comment in db.query(CommitmentComment).filter(CommitmentComment.created_at >= cutoff).all():
        recent_comments.append({
            "id": str(comment.id),
            "commitment_id": str(comment.commitment_id),
            "body": comment.body[:200],
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
        })

    return {
        "commitments_closed": commitments_closed,
        "commitments_opened": commitments_opened,
        "total_open": total_open,
        "overdue": overdue,
        "due_soon": due_soon,
        "active_initiatives": active_initiatives,
        "completed_initiatives": completed_initiatives,
        "stalled_initiatives": stalled_initiatives,
        "active_themes": active_themes,
        "recent_comments": recent_comments,
        "priorities": priorities,
        "extraction_date": now.isoformat(),
    }


# ---------------------------------------------------------------------------
# Strategy Confidence Score
# ---------------------------------------------------------------------------

def _compute_confidence_score(signals: dict) -> dict:
    """Compute a Strategy Confidence Score (0-100) from extracted signals.

    Components (each 0-100, weighted):
        - Execution Progress (35%): tasks closed vs total open
        - Momentum Signals (25%): new tasks opened, initiatives with movement
        - Alignment Signals (20%): initiatives connected to themes, priorities set
        - Friction Signals (20%): overdue tasks, stalled initiatives (reduces score)

    Returns dict with score, components, and explanation.
    """
    closed_count = len(signals.get("commitments_closed", []))
    opened_count = len(signals.get("commitments_opened", []))
    total_open = len(signals.get("total_open", []))
    overdue_count = len(signals.get("overdue", []))
    due_soon_count = len(signals.get("due_soon", []))
    active_init_count = len(signals.get("active_initiatives", []))
    stalled_count = len(signals.get("stalled_initiatives", []))
    completed_init_count = len(signals.get("completed_initiatives", []))
    priorities_count = len(signals.get("priorities", []))
    active_themes_count = len(signals.get("active_themes", []))

    # --- Execution Progress (0-100) ---
    # Measures throughput: how many tasks closed relative to total workload
    if total_open + closed_count > 0:
        execution_ratio = closed_count / (total_open + closed_count)
        execution_score = min(100, int(execution_ratio * 300))  # Scale up; 33% close rate = 100
    else:
        execution_score = 50  # Neutral if no tasks

    # Bonus for completing initiatives
    execution_score = min(100, execution_score + completed_init_count * 15)

    # --- Momentum Signals (0-100) ---
    # New work entering the system + initiatives showing task movement
    moving_initiatives = sum(
        1 for i in signals.get("active_initiatives", [])
        if i.get("tasks_closed_this_week", 0) > 0
    )
    if active_init_count > 0:
        movement_ratio = moving_initiatives / active_init_count
    else:
        movement_ratio = 0.5

    momentum_score = min(100, int(movement_ratio * 80))
    if opened_count > 0:
        momentum_score = min(100, momentum_score + 15)
    if closed_count > opened_count:
        momentum_score = min(100, momentum_score + 10)

    # --- Alignment Signals (0-100) ---
    # Are priorities set? Are themes defined? Are initiatives connected?
    alignment_score = 40  # Base
    if priorities_count > 0:
        alignment_score += 20
    if active_themes_count > 0:
        alignment_score += 20
    if active_init_count > 0:
        alignment_score += 20
    alignment_score = min(100, alignment_score)

    # --- Friction Signals (0-100, INVERTED — higher = less friction) ---
    friction_score = 100
    if total_open > 0:
        overdue_ratio = overdue_count / total_open
        friction_score -= int(overdue_ratio * 60)
    if active_init_count > 0:
        stalled_ratio = stalled_count / active_init_count
        friction_score -= int(stalled_ratio * 40)
    friction_score = max(0, friction_score)

    # --- Weighted composite ---
    composite = int(
        execution_score * 0.35
        + momentum_score * 0.25
        + alignment_score * 0.20
        + friction_score * 0.20
    )
    composite = max(0, min(100, composite))

    # --- Explanation ---
    parts = []
    if closed_count > 0:
        parts.append(f"{closed_count} task{'s' if closed_count != 1 else ''} completed this week")
    if completed_init_count > 0:
        parts.append(f"{completed_init_count} initiative{'s' if completed_init_count != 1 else ''} reached completion")
    if stalled_count > 0:
        parts.append(f"{stalled_count} initiative{'s' if stalled_count != 1 else ''} showing no movement")
    if overdue_count > 0:
        parts.append(f"{overdue_count} task{'s' if overdue_count != 1 else ''} overdue")
    if moving_initiatives > 0:
        parts.append(f"{moving_initiatives} of {active_init_count} initiatives showing active execution")

    explanation = ". ".join(parts) + "." if parts else "Insufficient data for detailed analysis."

    return {
        "score": composite,
        "components": {
            "execution": execution_score,
            "momentum": momentum_score,
            "alignment": alignment_score,
            "friction": friction_score,
        },
        "explanation": explanation,
    }


# ---------------------------------------------------------------------------
# Narrative Generation
# ---------------------------------------------------------------------------

def _build_narrative_execution_progress(signals: dict) -> dict:
    """Framing 1: Execution Progress — focuses on what got done and what's moving."""
    closed = signals.get("commitments_closed", [])
    opened = signals.get("commitments_opened", [])
    total_open = signals.get("total_open", [])
    active_inits = signals.get("active_initiatives", [])
    priorities = signals.get("priorities", [])

    # Paragraph 1: Week Summary
    closed_count = len(closed)
    opened_count = len(opened)
    total_count = len(total_open)
    moving_inits = [i for i in active_inits if i.get("tasks_closed_this_week", 0) > 0]

    if closed_count > 0:
        closed_titles = ", ".join(c["title"] for c in closed[:3])
        week_summary = (
            f"This week the team closed {closed_count} task{'s' if closed_count != 1 else ''}, "
            f"including {closed_titles}. "
        )
    else:
        week_summary = "No tasks were formally closed this week, though work continued across active workstreams. "

    if moving_inits:
        init_names = ", ".join(i["title"] for i in moving_inits[:3])
        week_summary += f"Execution momentum is visible across {init_names}."
    else:
        week_summary += f"The {len(active_inits)} active initiatives carried forward without formal closures."

    # Paragraph 2: Execution Focus
    if priorities:
        top_names = ", ".join(p["title"] for p in priorities[:3])
        exec_focus = (
            f"The current execution focus centers on {top_names}. "
            f"With {total_count} open tasks across {len(active_inits)} initiatives, "
            f"the team is maintaining a deliberate cadence of execution against the platform strategy."
        )
    else:
        exec_focus = (
            f"Across {total_count} open tasks and {len(active_inits)} active initiatives, "
            f"the team is sustaining execution pressure on the platform buildout. "
            f"Establishing explicit priority rankings would sharpen this focus further."
        )

    # Paragraph 3: Next Week
    due_soon = signals.get("due_soon", [])
    overdue = signals.get("overdue", [])
    if due_soon:
        due_titles = ", ".join(d["title"] for d in due_soon[:3])
        next_week = (
            f"Next week, attention turns to upcoming deadlines including {due_titles}. "
        )
    else:
        next_week = "Next week presents an opportunity to advance workstreams without immediate deadline pressure. "

    if overdue:
        next_week += (
            f"There {'are' if len(overdue) != 1 else 'is'} {len(overdue)} overdue "
            f"item{'s' if len(overdue) != 1 else ''} that should be resolved or rescheduled."
        )
    else:
        next_week += "All current deliverables are tracking within their timelines."

    body = f"{week_summary}\n\n{exec_focus}\n\n{next_week}"

    return {
        "framing": "Execution Progress",
        "strategic_objective": "Demonstrate consistent execution velocity against the platform strategy.",
        "why": "This framing emphasizes tangible output and closure rates, showing leadership that the team converts plans into deliverables.",
        "behavior": "Drives focus on completing tasks, closing loops, and moving initiatives forward measurably.",
        "body": body,
    }


def _build_narrative_momentum(signals: dict) -> dict:
    """Framing 2: Momentum — focuses on trajectory, growth, and expanding capability."""
    active_inits = signals.get("active_initiatives", [])
    closed = signals.get("commitments_closed", [])
    opened = signals.get("commitments_opened", [])
    total_open = signals.get("total_open", [])
    active_themes = signals.get("active_themes", [])
    completed_inits = signals.get("completed_initiatives", [])

    # Paragraph 1: Week Summary
    moving_inits = [i for i in active_inits if i.get("tasks_closed_this_week", 0) > 0]
    total_tasks_moved = sum(i.get("tasks_closed_this_week", 0) for i in active_inits)

    if total_tasks_moved > 0 or completed_inits:
        week_summary = (
            f"The platform continues to build momentum with {len(moving_inits)} initiatives showing "
            f"active execution this week. "
        )
        if completed_inits:
            names = ", ".join(i["title"] for i in completed_inits)
            week_summary += f"Notably, {names} reached completion, marking a strategic milestone. "
        week_summary += (
            f"Across the {len(active_inits)} active workstreams, the team is expanding capability "
            f"and deepening platform maturity."
        )
    else:
        week_summary = (
            f"The team sustained {len(active_inits)} active initiatives this week, maintaining "
            f"the foundation for accelerated delivery. While formal closures were limited, "
            f"the breadth of active work reflects growing platform ambition."
        )

    # Paragraph 2: Execution Focus
    if active_themes:
        theme_names = ", ".join(t["title"] for t in active_themes[:3])
        exec_focus = (
            f"Strategic themes around {theme_names} continue to shape the execution agenda. "
            f"The {len(opened)} new tasks opened this week signal that the platform scope is "
            f"expanding deliberately rather than contracting."
        )
    else:
        exec_focus = (
            f"With {len(opened)} new tasks entering the system and {len(active_inits)} initiatives "
            f"in flight, the team is building the operational infrastructure that scales. "
            f"The trajectory suggests accelerating capability rather than plateauing."
        )

    # Paragraph 3: Next Week
    next_week = (
        f"The coming week is an opportunity to convert momentum into measurable outcomes. "
        f"With {len(total_open)} tasks in the pipeline and {len(active_inits)} active initiatives, "
        f"the team is positioned to demonstrate that platform investment is compounding."
    )

    body = f"{week_summary}\n\n{exec_focus}\n\n{next_week}"

    return {
        "framing": "Momentum",
        "strategic_objective": "Show that the platform is accelerating and capability is compounding week over week.",
        "why": "This framing highlights trajectory and growth, reassuring leadership that investment in the platform is paying off and building toward a tipping point.",
        "behavior": "Drives focus on expanding capability, opening new workstreams, and demonstrating that the platform is getting stronger, not just busier.",
        "body": body,
    }


def _build_narrative_alignment(signals: dict) -> dict:
    """Framing 3: Alignment — focuses on how execution connects to strategy."""
    active_inits = signals.get("active_initiatives", [])
    active_themes = signals.get("active_themes", [])
    closed = signals.get("commitments_closed", [])
    priorities = signals.get("priorities", [])
    stalled = signals.get("stalled_initiatives", [])
    total_open = signals.get("total_open", [])

    # Paragraph 1: Week Summary
    if active_themes:
        theme_count = len(active_themes)
        theme_names = ", ".join(t["title"] for t in active_themes[:3])
        week_summary = (
            f"This week's execution aligned across {theme_count} strategic "
            f"theme{'s' if theme_count != 1 else ''} — {theme_names}. "
        )
    else:
        week_summary = "This week the team advanced platform execution across multiple workstreams. "

    if closed:
        week_summary += (
            f"The {len(closed)} completed task{'s' if len(closed) != 1 else ''} directly "
            f"support the broader strategic objective of building the AI-native operational backbone."
        )
    else:
        week_summary += (
            f"While no tasks formally closed, the {len(active_inits)} active initiatives "
            f"continued driving toward the strategic objective."
        )

    # Paragraph 2: Execution Focus
    if priorities and active_inits:
        exec_focus = (
            f"Priority alignment remains strong with {len(priorities)} explicitly ranked items "
            f"guiding daily execution. Each of the {len(active_inits)} active initiatives connects "
            f"to the platform strategy, ensuring that tactical work contributes to long-term "
            f"program objectives."
        )
    else:
        exec_focus = (
            f"The {len(active_inits)} active initiatives represent the operational surface area "
            f"of the platform strategy. Strengthening the connection between daily tasks and "
            f"strategic themes will deepen alignment and improve execution coherence."
        )

    # Paragraph 3: Next Week
    if stalled:
        stalled_names = ", ".join(s["title"] for s in stalled[:3])
        next_week = (
            f"Next week, attention should turn to realigning {stalled_names}, "
            f"{'which have' if len(stalled) != 1 else 'which has'} shown limited movement. "
            f"Resolving these gaps ensures that the full initiative portfolio remains "
            f"strategically coherent."
        )
    else:
        next_week = (
            f"Looking ahead, the team is well-positioned to deepen alignment between execution "
            f"and strategy. With {len(total_open)} tasks in flight across {len(active_inits)} "
            f"initiatives, every workstream contributes to the platform's strategic trajectory."
        )

    body = f"{week_summary}\n\n{exec_focus}\n\n{next_week}"

    return {
        "framing": "Alignment",
        "strategic_objective": "Demonstrate that every workstream connects to the platform strategy and nothing is drifting.",
        "why": "This framing shows leadership that execution is strategically coherent, not just busy. Every task and initiative serves the larger program objective.",
        "behavior": "Drives focus on strategic coherence, connecting daily work to long-term goals, and identifying misaligned workstreams early.",
        "body": body,
    }


def generate_narratives(signals: dict) -> list[dict]:
    """Generate three narrative options with different strategic framings.

    Each narrative contains ~150-200 words, 3 paragraphs (Week Summary,
    Execution Focus, Next Week). No bullet lists — prose only.
    """
    return [
        _build_narrative_execution_progress(signals),
        _build_narrative_momentum(signals),
        _build_narrative_alignment(signals),
    ]


def _select_recommended_narrative(signals: dict, narratives: list[dict]) -> tuple[int, str]:
    """Select the most appropriate narrative based on current signals.

    Returns (index, reason).
    """
    closed_count = len(signals.get("commitments_closed", []))
    stalled_count = len(signals.get("stalled_initiatives", []))
    completed_inits = len(signals.get("completed_initiatives", []))
    active_inits = len(signals.get("active_initiatives", []))
    moving_inits = sum(
        1 for i in signals.get("active_initiatives", [])
        if i.get("tasks_closed_this_week", 0) > 0
    )

    # If lots of closures — lead with Execution Progress
    if closed_count >= 3:
        return 0, (
            f"Execution Progress is recommended because {closed_count} tasks were closed "
            f"this week, providing strong evidence of delivery velocity."
        )

    # If initiatives are completing or strong movement — lead with Momentum
    if completed_inits > 0 or (active_inits > 0 and moving_inits >= active_inits * 0.6):
        return 1, (
            "Momentum is recommended because the team is showing strong forward movement "
            "across initiatives, indicating accelerating platform capability."
        )

    # If stalled initiatives — lead with Alignment to address gaps
    if stalled_count > 0:
        return 2, (
            f"Alignment is recommended because {stalled_count} initiative{'s' if stalled_count != 1 else ''} "
            f"{'are' if stalled_count != 1 else 'is'} showing limited movement, and this framing "
            f"helps leadership understand how execution connects to strategy despite friction."
        )

    # Default: Execution Progress (most concrete)
    return 0, (
        "Execution Progress is recommended as the default framing, providing "
        "the most concrete view of what the team delivered this week."
    )


# ---------------------------------------------------------------------------
# Narrative Continuity
# ---------------------------------------------------------------------------

def _build_narrative_continuity(
    signals: dict,
    previous_update: Optional[WeeklyStrategyUpdate],
) -> str:
    """Build the Strategic Narrative Continuity section.

    Explains how this week's execution contributes to the long-term mission
    and references the previous week's themes for context.
    """
    active_inits = signals.get("active_initiatives", [])
    closed = signals.get("commitments_closed", [])
    active_themes = signals.get("active_themes", [])

    parts = []
    parts.append(
        "The AI Platform Strategic Narrative continues to evolve through "
        "consistent weekly execution."
    )

    if active_themes:
        theme_names = ", ".join(t["title"] for t in active_themes[:3])
        parts.append(
            f"This week's work directly advances the strategic themes of {theme_names}, "
            f"reinforcing the long-term vision of building an AI-native operational backbone."
        )

    if closed:
        parts.append(
            f"The {len(closed)} completed deliverable{'s' if len(closed) != 1 else ''} "
            f"represent tangible progress that compounds over time."
        )

    if previous_update:
        prev_score = previous_update.confidence_score
        if prev_score is not None:
            parts.append(
                f"Last week's Strategy Confidence Score was {prev_score}. "
                f"This week's score reflects the continued trajectory of platform execution."
            )

    parts.append(
        "Each week of sustained execution deepens the platform's strategic position "
        "and moves the organization closer to its AI-native operating model."
    )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Forwardable Version
# ---------------------------------------------------------------------------

def _build_forwardable_body(
    recommended_narrative: dict,
    score_data: dict,
) -> str:
    """Build a clean, ready-to-forward version for Brian to send to the team.

    This is the version Brian forwards — no strategy options, no scoring
    details. Just the selected narrative as a polished update.
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%B %-d, %Y")

    lines = []
    lines.append(f"AI Platform — Weekly Execution Update ({date_str})")
    lines.append("")
    lines.append(recommended_narrative["body"])
    lines.append("")
    lines.append(f"Strategy Confidence: {score_data['score']}/100")
    lines.append("")
    lines.append(
        "This update reflects the most meaningful execution signals from the "
        "past week. Please reach out with any questions."
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Week-over-week Trend
# ---------------------------------------------------------------------------

def _compute_trend(
    current_score: int,
    previous_update: Optional[WeeklyStrategyUpdate],
) -> str:
    """Compute the trend direction based on previous week's score."""
    if not previous_update or previous_update.confidence_score is None:
        return "stable"
    prev = previous_update.confidence_score
    diff = current_score - prev
    if diff >= 5:
        return "up"
    elif diff <= -5:
        return "down"
    return "stable"


# ---------------------------------------------------------------------------
# Email Composition
# ---------------------------------------------------------------------------

def compose_update_email(update: WeeklyStrategyUpdate) -> str:
    """Compose the full email body for Brian with all sections.

    Structure:
    1. Greeting
    2. Narrative Option 1 (with strategic explanation)
    3. Narrative Option 2 (with strategic explanation)
    4. Narrative Option 3 (with strategic explanation)
    5. Recommended Narrative (which one and why)
    6. Strategic Narrative Continuity
    7. Strategy Confidence Signal
    8. Forwardable Version
    """
    narratives = json.loads(update.narrative_options) if update.narrative_options else []
    score_components = json.loads(update.score_components) if update.score_components else {}

    date_str = update.week_start_date.strftime("%B %-d, %Y")

    lines = []

    # 1. Greeting
    lines.append(f"Brian,")
    lines.append("")
    lines.append(
        f"Here is your Friday Strategic Execution Update for the week of {date_str}. "
        f"Below you'll find three narrative options for how to frame this week's "
        f"progress, along with a recommended selection and a ready-to-forward version."
    )
    lines.append("")

    # 2-4. Three Narrative Options
    for idx, narrative in enumerate(narratives):
        option_num = idx + 1
        lines.append(f"--- NARRATIVE OPTION {option_num}: {narrative['framing'].upper()} ---")
        lines.append("")
        lines.append(f"Strategic Objective: {narrative['strategic_objective']}")
        lines.append(f"Why This Framing Works: {narrative['why']}")
        lines.append(f"Behavior It Drives: {narrative['behavior']}")
        lines.append("")
        lines.append(narrative["body"])
        lines.append("")

    # 5. Recommended Narrative
    rec_idx = update.recommended_narrative or 0
    if rec_idx < len(narratives):
        rec_name = narratives[rec_idx]["framing"]
    else:
        rec_name = "Execution Progress"
    lines.append("--- RECOMMENDED NARRATIVE ---")
    lines.append("")
    lines.append(f"Recommended: Option {rec_idx + 1} ({rec_name})")
    lines.append("")

    # 6. Strategic Narrative Continuity
    lines.append("--- STRATEGIC NARRATIVE CONTINUITY ---")
    lines.append("")
    lines.append(update.narrative_continuity or "")
    lines.append("")

    # 7. Strategy Confidence Signal
    trend_arrow = {"up": "(trending up)", "down": "(trending down)", "stable": "(stable)"}
    trend_label = trend_arrow.get(update.confidence_trend or "stable", "(stable)")
    lines.append("--- STRATEGY CONFIDENCE SIGNAL ---")
    lines.append("")
    lines.append(f"Score: {update.confidence_score}/100 {trend_label}")
    if score_components:
        lines.append(f"  Execution: {score_components.get('execution', 'N/A')}/100")
        lines.append(f"  Momentum: {score_components.get('momentum', 'N/A')}/100")
        lines.append(f"  Alignment: {score_components.get('alignment', 'N/A')}/100")
        lines.append(f"  Friction (inverted): {score_components.get('friction', 'N/A')}/100")
    lines.append(f"Explanation: {update.confidence_explanation or 'N/A'}")
    lines.append("")

    # 8. Forwardable Version
    lines.append("--- FORWARDABLE VERSION (copy below to forward to the team) ---")
    lines.append("")
    lines.append(update.forwardable_body or "")
    lines.append("")

    return "\n".join(lines)


def send_update_email(update: WeeklyStrategyUpdate) -> bool:
    """Send the Friday update email to Brian via Gmail.

    Uses SMTP with an app password (env vars GMAIL_USER and GMAIL_APP_PASSWORD).
    Returns True on success.
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    gmail_user = os.environ.get("GMAIL_USER")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("FRIDAY_UPDATE_RECIPIENT", gmail_user)

    if not gmail_user or not gmail_password:
        log.warning("Gmail credentials not configured — skipping Friday update email")
        return False

    if not recipient:
        log.warning("No recipient configured — skipping Friday update email")
        return False

    date_str = update.week_start_date.strftime("%B %-d, %Y")
    subject = f"Friday Strategic Execution Update — {date_str}"

    email_body = compose_update_email(update)

    msg = MIMEMultipart()
    msg["From"] = gmail_user
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(email_body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, [recipient], msg.as_string())
        log.info("Friday update email sent to %s", recipient)
        return True
    except Exception:
        log.exception("Failed to send Friday update email")
        return False


# ---------------------------------------------------------------------------
# Main Generation Pipeline
# ---------------------------------------------------------------------------

def generate_friday_update(
    db: Session,
    *,
    send_email: bool = True,
) -> WeeklyStrategyUpdate:
    """Generate the complete Friday Strategic Execution Update.

    Pipeline:
    1. Extract signals from past 7 days
    2. Find previous week's update for trend comparison
    3. Compute Strategy Confidence Score
    4. Generate three narrative options
    5. Select recommended narrative
    6. Build narrative continuity section
    7. Build forwardable version
    8. Persist to database
    9. Send email (if configured)

    Returns the saved WeeklyStrategyUpdate record.
    """
    now = datetime.now(timezone.utc)
    week_start = _week_start(now)

    # 1. Extract signals
    signals = extract_signals(db, now=now)

    # 2. Find previous update
    previous_update = (
        db.query(WeeklyStrategyUpdate)
        .filter(WeeklyStrategyUpdate.week_start_date < week_start)
        .order_by(WeeklyStrategyUpdate.created_at.desc())
        .first()
    )

    # 3. Compute confidence score
    score_data = _compute_confidence_score(signals)

    # 4. Compute trend
    trend = _compute_trend(score_data["score"], previous_update)

    # 5. Generate three narrative options
    narratives = generate_narratives(signals)

    # 6. Select recommended narrative
    rec_idx, rec_reason = _select_recommended_narrative(signals, narratives)

    # 7. Build narrative continuity
    continuity = _build_narrative_continuity(signals, previous_update)

    # 8. Build forwardable version
    forwardable = _build_forwardable_body(narratives[rec_idx], score_data)

    # 9. Persist
    update = WeeklyStrategyUpdate(
        id=uuid.uuid4(),
        week_start_date=week_start,
        status=UpdateStatus.DRAFT,
        narrative_options=json.dumps(narratives),
        recommended_narrative=rec_idx,
        confidence_score=score_data["score"],
        confidence_trend=trend,
        confidence_explanation=score_data["explanation"],
        score_components=json.dumps(score_data["components"]),
        narrative_continuity=continuity,
        forwardable_body=forwardable,
        signal_snapshot=json.dumps(signals),
        previous_update_id=previous_update.id if previous_update else None,
    )
    db.add(update)
    db.commit()
    db.refresh(update)

    # 10. Send email
    if send_email:
        sent = send_update_email(update)
        if sent:
            update.status = UpdateStatus.SENT
            db.commit()
            db.refresh(update)

    log.info(
        "Friday update generated: id=%s score=%s trend=%s recommended=%s",
        update.id, update.confidence_score, update.confidence_trend,
        narratives[rec_idx]["framing"],
    )

    return update


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def get_update(db: Session, *, update_id: str) -> Optional[WeeklyStrategyUpdate]:
    """Get a single update by ID."""
    return (
        db.query(WeeklyStrategyUpdate)
        .filter(WeeklyStrategyUpdate.id == uuid.UUID(update_id))
        .first()
    )


def list_updates(
    db: Session,
    *,
    limit: int = 10,
) -> list[WeeklyStrategyUpdate]:
    """List updates, newest first."""
    return (
        db.query(WeeklyStrategyUpdate)
        .order_by(WeeklyStrategyUpdate.created_at.desc())
        .limit(limit)
        .all()
    )


def get_latest_update(db: Session) -> Optional[WeeklyStrategyUpdate]:
    """Get the most recent update."""
    return (
        db.query(WeeklyStrategyUpdate)
        .order_by(WeeklyStrategyUpdate.created_at.desc())
        .first()
    )
