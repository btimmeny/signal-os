"""Tests for Feature 022 — Strategic Execution Intelligence System.

Covers:
- StrategicContributionNotes generated/stored on task open
- ExecutionImpactNotes generated/stored on task close
- StrategicNarrative records created for weekly understanding
- StrategyConfidenceHistory with trend direction
- WeeklyNarrative drafts (3 per week) with recommended flag
- Strategy Confidence Score calculation (40/25/20 weighting)
- Idempotency (no duplicates on re-run)
- Session independence (data loaded from DB, not memory)
- Clarification prompt mechanism
- Email composition with correct structure
- Confidence band labels
- API endpoints
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import HEADERS

from app.models import (
    Commitment,
    CommitmentStatus,
    ExecutionImpactNote,
    Initiative,
    InitiativeCommitmentLink,
    InitiativeStatus,
    StrategicContributionNote,
    StrategicNarrative,
    StrategicSignal,
    StrategicTheme,
    StrategyConfidenceHistory,
    StrategyDebriefRecord,
    ThemeStatus,
    WeeklyNarrative,
    WeeklyReviewSession,
    WeeklyStrategyUpdate,
)
from app.services import strategic_intelligence as intel_svc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_commitment(db, title="Test task", description=None, status="OPEN"):
    c = Commitment(
        id=uuid.uuid4(),
        title=title,
        description=description,
        status=CommitmentStatus(status),
        opened_at=datetime.now(timezone.utc),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _create_theme(db, title="AI Platform"):
    t = StrategicTheme(
        id=uuid.uuid4(),
        title=title,
        status=ThemeStatus.ACTIVE,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _create_initiative(db, title="Build agent infrastructure", theme=None):
    i = Initiative(
        id=uuid.uuid4(),
        title=title,
        status=InitiativeStatus.ACTIVE,
        theme_id=theme.id if theme else None,
    )
    db.add(i)
    db.commit()
    db.refresh(i)
    return i


def _link_commitment_to_initiative(db, commitment, initiative):
    link = InitiativeCommitmentLink(
        id=uuid.uuid4(),
        commitment_id=commitment.id,
        initiative_id=initiative.id,
    )
    db.add(link)
    db.commit()
    return link


def _close_commitment(db, commitment):
    commitment.status = CommitmentStatus.CLOSED
    commitment.closed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(commitment)
    return commitment


# ---------------------------------------------------------------------------
# SECTION 1 — Contribution Notes (task open)
# ---------------------------------------------------------------------------


class TestContributionNotes:
    """Test StrategicContributionNote generation on task open."""

    def test_contribution_note_created_on_open(self, db_session):
        """Opening a task creates a contribution note."""
        c = _create_commitment(db_session, title="Deploy API gateway")
        note = intel_svc.record_contribution_note(db_session, c)

        assert note is not None
        assert note.task_id == c.id
        assert note.strategic_contribution_note
        assert note.source == "inferred"
        assert note.created_at is not None

    def test_contribution_note_with_initiative(self, db_session):
        """Contribution note references linked initiative."""
        theme = _create_theme(db_session)
        init = _create_initiative(db_session, title="API Gateway", theme=theme)
        c = _create_commitment(db_session, title="Build gateway endpoint")
        _link_commitment_to_initiative(db_session, c, init)

        note = intel_svc.record_contribution_note(db_session, c)

        assert "API Gateway" in note.strategic_contribution_note
        assert note.initiative_id == init.id
        assert note.strategic_theme == theme.title

    def test_contribution_note_with_theme_only(self, db_session):
        """Contribution note with theme but no initiative still works."""
        c = _create_commitment(db_session, title="Build new feature")

        note = intel_svc.record_contribution_note(db_session, c)

        assert note is not None
        assert note.strategic_contribution_note
        assert note.source == "inferred"

    def test_contribution_note_unclear_contribution(self, db_session):
        """Tasks with no initiative/theme get flagged as unclear."""
        c = _create_commitment(db_session, title="Fix random bug")

        note = intel_svc.record_contribution_note(db_session, c)

        assert "unclear" in note.strategic_contribution_note.lower()
        assert note.initiative_id is None

    def test_contribution_note_idempotent(self, db_session):
        """Running twice for the same task returns the same note."""
        c = _create_commitment(db_session, title="Deploy service")

        note1 = intel_svc.record_contribution_note(db_session, c)
        note2 = intel_svc.record_contribution_note(db_session, c)

        assert note1.id == note2.id

        # Verify only one record in DB
        count = (
            db_session.query(StrategicContributionNote)
            .filter(StrategicContributionNote.task_id == c.id)
            .count()
        )
        assert count == 1

    def test_list_contribution_notes(self, db_session):
        """List contribution notes from the database."""
        c1 = _create_commitment(db_session, title="Task A")
        c2 = _create_commitment(db_session, title="Task B")
        intel_svc.record_contribution_note(db_session, c1)
        intel_svc.record_contribution_note(db_session, c2)

        notes = intel_svc.list_contribution_notes(db_session)
        assert len(notes) == 2

    def test_get_unclear_contributions(self, db_session):
        """Get contributions needing clarification."""
        c1 = _create_commitment(db_session, title="Fix bug")
        c2 = _create_commitment(db_session, title="Deploy platform")
        init = _create_initiative(db_session)
        _link_commitment_to_initiative(db_session, c2, init)

        intel_svc.record_contribution_note(db_session, c1)
        intel_svc.record_contribution_note(db_session, c2)

        unclear = intel_svc.get_unclear_contributions(db_session)
        assert len(unclear) == 1
        assert unclear[0].task_id == c1.id

    def test_confirm_contribution_note(self, db_session):
        """Brian can confirm/update a contribution note."""
        c = _create_commitment(db_session, title="Fix bug")
        note = intel_svc.record_contribution_note(db_session, c)

        updated = intel_svc.confirm_contribution_note(
            db_session,
            str(note.id),
            updated_text="This task supports the CI/CD initiative.",
            strategic_theme="DevOps",
        )

        assert updated is not None
        assert updated.source == "user_confirmed"
        assert "CI/CD" in updated.strategic_contribution_note
        assert updated.strategic_theme == "DevOps"


# ---------------------------------------------------------------------------
# SECTION 2 — Impact Notes (task close)
# ---------------------------------------------------------------------------


class TestImpactNotes:
    """Test ExecutionImpactNote generation on task close."""

    def test_impact_note_created_on_close(self, db_session):
        """Closing a task creates an impact note."""
        c = _create_commitment(db_session, title="Deploy API gateway")
        _close_commitment(db_session, c)

        note = intel_svc.record_impact_note(db_session, c)

        assert note is not None
        assert note.task_id == c.id
        assert note.execution_impact_note
        assert note.created_at is not None

    def test_impact_note_with_initiative(self, db_session):
        """Impact note references linked initiative."""
        theme = _create_theme(db_session, title="Infrastructure")
        init = _create_initiative(db_session, title="API Gateway", theme=theme)
        c = _create_commitment(db_session, title="Build gateway endpoint")
        _link_commitment_to_initiative(db_session, c, init)
        _close_commitment(db_session, c)

        note = intel_svc.record_impact_note(db_session, c)

        assert "API Gateway" in note.execution_impact_note
        assert note.initiative_id == init.id

    def test_impact_note_strategic_signal_flag(self, db_session):
        """High-signal tasks get flagged appropriately."""
        init = _create_initiative(db_session, title="Platform Build")
        c = _create_commitment(
            db_session,
            title="Deploy infrastructure pipeline",
        )
        _link_commitment_to_initiative(db_session, c, init)
        _close_commitment(db_session, c)

        note = intel_svc.record_impact_note(db_session, c)

        assert note.strategic_signal_flag == 1

    def test_impact_note_low_signal(self, db_session):
        """Non-strategic tasks don't get flagged as signals."""
        c = _create_commitment(db_session, title="Update meeting notes")
        _close_commitment(db_session, c)

        note = intel_svc.record_impact_note(db_session, c)

        assert note.strategic_signal_flag == 0

    def test_impact_note_idempotent(self, db_session):
        """Running twice for the same task returns the same note."""
        c = _create_commitment(db_session, title="Deploy service")
        _close_commitment(db_session, c)

        note1 = intel_svc.record_impact_note(db_session, c)
        note2 = intel_svc.record_impact_note(db_session, c)

        assert note1.id == note2.id

        count = (
            db_session.query(ExecutionImpactNote)
            .filter(ExecutionImpactNote.task_id == c.id)
            .count()
        )
        assert count == 1

    def test_list_impact_notes(self, db_session):
        """List impact notes from the database."""
        c1 = _create_commitment(db_session, title="Task A")
        c2 = _create_commitment(db_session, title="Task B")
        _close_commitment(db_session, c1)
        _close_commitment(db_session, c2)
        intel_svc.record_impact_note(db_session, c1)
        intel_svc.record_impact_note(db_session, c2)

        notes = intel_svc.list_impact_notes(db_session)
        assert len(notes) == 2

    def test_get_high_signal_impact_notes(self, db_session):
        """Get impact notes flagged as strategic signals."""
        init = _create_initiative(db_session, title="Platform")
        c1 = _create_commitment(db_session, title="Deploy infrastructure pipeline")
        _link_commitment_to_initiative(db_session, c1, init)
        c2 = _create_commitment(db_session, title="Update readme")
        _close_commitment(db_session, c1)
        _close_commitment(db_session, c2)
        intel_svc.record_impact_note(db_session, c1)
        intel_svc.record_impact_note(db_session, c2)

        high_signal = intel_svc.get_high_signal_impact_notes(db_session)
        assert len(high_signal) == 1
        assert high_signal[0].task_id == c1.id


# ---------------------------------------------------------------------------
# SECTION 3 — Strategic Narrative
# ---------------------------------------------------------------------------


class TestStrategicNarrative:
    """Test StrategicNarrative record management."""

    def test_narrative_created(self, db_session):
        """StrategicNarrative is created for a week."""
        signals = {
            "commitments_closed": [{"title": "Task A"}],
            "commitments_opened": [{"title": "Task B"}],
            "overdue": [],
            "stalled_initiatives": [],
            "active_themes": [{"title": "AI Platform"}],
            "active_initiatives": [
                {"title": "Agent Build", "tasks_closed_this_week": 1}
            ],
        }
        week = intel_svc._week_start()

        narrative = intel_svc._build_strategic_narrative_record(
            db_session, signals, week
        )

        assert narrative is not None
        # SQLite strips tzinfo, so compare without timezone
        assert narrative.date.replace(tzinfo=None) == week.replace(tzinfo=None)
        assert narrative.strategic_objective is not None
        assert narrative.narrative_summary is not None
        assert "1 tasks completed" in narrative.narrative_summary or "1 task" in narrative.narrative_summary

    def test_narrative_idempotent(self, db_session):
        """Running twice for the same week updates, doesn't duplicate."""
        signals = {
            "commitments_closed": [{"title": "Task A"}],
            "commitments_opened": [],
            "overdue": [],
            "stalled_initiatives": [],
            "active_themes": [],
            "active_initiatives": [],
        }
        week = intel_svc._week_start()

        n1 = intel_svc._build_strategic_narrative_record(
            db_session, signals, week
        )

        # Run again with different data
        signals2 = {
            "commitments_closed": [{"title": "Task A"}, {"title": "Task B"}],
            "commitments_opened": [],
            "overdue": [],
            "stalled_initiatives": [],
            "active_themes": [],
            "active_initiatives": [],
        }
        n2 = intel_svc._build_strategic_narrative_record(
            db_session, signals2, week
        )

        assert n1.id == n2.id  # Same record updated, not duplicated
        assert "2 tasks" in n2.narrative_summary

        # Verify only one record
        count = (
            db_session.query(StrategicNarrative)
            .filter(StrategicNarrative.date == week)
            .count()
        )
        assert count == 1

    def test_narrative_with_friction(self, db_session):
        """Narrative includes friction signals (overdue, stalled)."""
        signals = {
            "commitments_closed": [],
            "commitments_opened": [],
            "overdue": [{"title": "Overdue task"}],
            "stalled_initiatives": [{"title": "Stalled init"}],
            "active_themes": [],
            "active_initiatives": [
                {"title": "Active init", "tasks_closed_this_week": 0}
            ],
        }
        week = intel_svc._week_start()

        narrative = intel_svc._build_strategic_narrative_record(
            db_session, signals, week
        )

        friction = json.loads(narrative.friction_signals)
        assert len(friction) > 0
        assert any("Overdue" in f for f in friction) or any("Stalled" in f for f in friction)

    def test_list_strategic_narratives(self, db_session):
        """List recent strategic narratives."""
        signals = {
            "commitments_closed": [],
            "commitments_opened": [],
            "overdue": [],
            "stalled_initiatives": [],
            "active_themes": [],
            "active_initiatives": [],
        }

        week1 = intel_svc._week_start()
        week2 = week1 - timedelta(days=7)

        intel_svc._build_strategic_narrative_record(db_session, signals, week1)
        intel_svc._build_strategic_narrative_record(db_session, signals, week2)

        narratives = intel_svc.list_strategic_narratives(db_session)
        assert len(narratives) == 2


# ---------------------------------------------------------------------------
# SECTION 4 — Strategy Confidence History
# ---------------------------------------------------------------------------


class TestConfidenceHistory:
    """Test StrategyConfidenceHistory tracking."""

    def test_confidence_record_created(self, db_session):
        """Confidence history record is created."""
        week = intel_svc._week_start()

        record = intel_svc._record_confidence_history(
            db_session, score=65, explanation="Strong execution", week_date=week
        )

        assert record is not None
        assert record.confidence_score == 65
        assert record.confidence_explanation == "Strong execution"
        assert record.trend_direction == "flat"  # No previous
        assert record.previous_score is None

    def test_confidence_trend_improving(self, db_session):
        """Trend direction calculated correctly (improving)."""
        week1 = intel_svc._week_start() - timedelta(days=7)
        week2 = intel_svc._week_start()

        intel_svc._record_confidence_history(
            db_session, score=50, explanation="Week 1", week_date=week1
        )
        record = intel_svc._record_confidence_history(
            db_session, score=70, explanation="Week 2", week_date=week2
        )

        assert record.trend_direction == "improving"
        assert record.previous_score == 50

    def test_confidence_trend_declining(self, db_session):
        """Trend direction calculated correctly (declining)."""
        week1 = intel_svc._week_start() - timedelta(days=7)
        week2 = intel_svc._week_start()

        intel_svc._record_confidence_history(
            db_session, score=70, explanation="Week 1", week_date=week1
        )
        record = intel_svc._record_confidence_history(
            db_session, score=50, explanation="Week 2", week_date=week2
        )

        assert record.trend_direction == "declining"
        assert record.previous_score == 70

    def test_confidence_trend_flat(self, db_session):
        """Trend direction calculated correctly (flat, within ±5)."""
        week1 = intel_svc._week_start() - timedelta(days=7)
        week2 = intel_svc._week_start()

        intel_svc._record_confidence_history(
            db_session, score=60, explanation="Week 1", week_date=week1
        )
        record = intel_svc._record_confidence_history(
            db_session, score=63, explanation="Week 2", week_date=week2
        )

        assert record.trend_direction == "flat"

    def test_confidence_idempotent_same_score(self, db_session):
        """Same score doesn't trigger an update."""
        week = intel_svc._week_start()

        r1 = intel_svc._record_confidence_history(
            db_session, score=65, explanation="First", week_date=week
        )
        r2 = intel_svc._record_confidence_history(
            db_session, score=65, explanation="Second", week_date=week
        )

        assert r1.id == r2.id
        assert r2.confidence_explanation == "First"  # Not updated

    def test_confidence_idempotent_different_score(self, db_session):
        """Different score updates the existing record."""
        week = intel_svc._week_start()

        r1 = intel_svc._record_confidence_history(
            db_session, score=65, explanation="First", week_date=week
        )
        r2 = intel_svc._record_confidence_history(
            db_session, score=75, explanation="Improved", week_date=week
        )

        assert r1.id == r2.id
        assert r2.confidence_score == 75
        assert r2.confidence_explanation == "Improved"

        # Verify only one record
        count = (
            db_session.query(StrategyConfidenceHistory)
            .filter(StrategyConfidenceHistory.date == week)
            .count()
        )
        assert count == 1

    def test_get_confidence_history(self, db_session):
        """Get confidence history list."""
        week1 = intel_svc._week_start() - timedelta(days=7)
        week2 = intel_svc._week_start()

        intel_svc._record_confidence_history(
            db_session, score=50, explanation="W1", week_date=week1
        )
        intel_svc._record_confidence_history(
            db_session, score=65, explanation="W2", week_date=week2
        )

        history = intel_svc.get_confidence_history(db_session)
        assert len(history) == 2
        assert history[0].confidence_score == 65  # Most recent first

    def test_get_latest_confidence(self, db_session):
        """Get the most recent confidence record."""
        week1 = intel_svc._week_start() - timedelta(days=7)
        week2 = intel_svc._week_start()

        intel_svc._record_confidence_history(
            db_session, score=50, explanation="W1", week_date=week1
        )
        intel_svc._record_confidence_history(
            db_session, score=65, explanation="W2", week_date=week2
        )

        latest = intel_svc.get_latest_confidence(db_session)
        assert latest is not None
        assert latest.confidence_score == 65


# ---------------------------------------------------------------------------
# SECTION 5 — Weekly Narratives (3 drafts)
# ---------------------------------------------------------------------------


class TestWeeklyNarratives:
    """Test WeeklyNarrative record management."""

    def test_three_narratives_created(self, db_session):
        """Three narrative drafts are created per week."""
        week = intel_svc._week_start()
        narratives = [
            {
                "framing": "Execution Progress",
                "strategic_objective": "Demonstrate velocity",
                "body": "The team closed 5 tasks this week...",
            },
            {
                "framing": "Momentum",
                "strategic_objective": "Show acceleration",
                "body": "Platform capability continues to compound...",
            },
            {
                "framing": "Alignment",
                "strategic_objective": "Connect to strategy",
                "body": "Execution aligns across 3 themes...",
            },
        ]

        results = intel_svc._record_weekly_narratives(
            db_session, narratives, recommended_idx=0, week_date=week
        )

        assert len(results) == 3
        types = {r.narrative_type for r in results}
        assert types == {"execution_progress", "momentum", "alignment"}

    def test_recommended_flag_set(self, db_session):
        """Only the recommended narrative has the flag set."""
        week = intel_svc._week_start()
        narratives = [
            {"framing": "EP", "strategic_objective": "V", "body": "..."},
            {"framing": "M", "strategic_objective": "A", "body": "..."},
            {"framing": "AL", "strategic_objective": "C", "body": "..."},
        ]

        results = intel_svc._record_weekly_narratives(
            db_session, narratives, recommended_idx=1, week_date=week
        )

        recommended = [r for r in results if r.recommended_flag == 1]
        assert len(recommended) == 1
        assert recommended[0].narrative_type == "momentum"

    def test_narratives_idempotent(self, db_session):
        """Re-running updates existing narratives, doesn't duplicate."""
        week = intel_svc._week_start()
        narratives = [
            {"framing": "EP", "strategic_objective": "V", "body": "Version 1"},
            {"framing": "M", "strategic_objective": "A", "body": "Version 1"},
            {"framing": "AL", "strategic_objective": "C", "body": "Version 1"},
        ]

        r1 = intel_svc._record_weekly_narratives(
            db_session, narratives, recommended_idx=0, week_date=week
        )

        narratives2 = [
            {"framing": "EP", "strategic_objective": "V", "body": "Version 2"},
            {"framing": "M", "strategic_objective": "A", "body": "Version 2"},
            {"framing": "AL", "strategic_objective": "C", "body": "Version 2"},
        ]

        r2 = intel_svc._record_weekly_narratives(
            db_session, narratives2, recommended_idx=2, week_date=week
        )

        # Same IDs
        for i in range(3):
            assert r1[i].id == r2[i].id

        # Updated content
        assert r2[0].narrative_text == "Version 2"

        # Only 3 records total
        count = (
            db_session.query(WeeklyNarrative)
            .filter(WeeklyNarrative.week_date == week)
            .count()
        )
        assert count == 3

    def test_get_weekly_narratives(self, db_session):
        """Get all narrative drafts for a week."""
        week = intel_svc._week_start()
        narratives = [
            {"framing": "EP", "strategic_objective": "V", "body": "..."},
            {"framing": "M", "strategic_objective": "A", "body": "..."},
            {"framing": "AL", "strategic_objective": "C", "body": "..."},
        ]
        intel_svc._record_weekly_narratives(
            db_session, narratives, recommended_idx=0, week_date=week
        )

        results = intel_svc.get_weekly_narratives(db_session, week_date=week)
        assert len(results) == 3

    def test_get_recommended_narrative(self, db_session):
        """Get the recommended narrative for a week."""
        week = intel_svc._week_start()
        narratives = [
            {"framing": "EP", "strategic_objective": "V", "body": "Body EP"},
            {"framing": "M", "strategic_objective": "A", "body": "Body M"},
            {"framing": "AL", "strategic_objective": "C", "body": "Body AL"},
        ]
        intel_svc._record_weekly_narratives(
            db_session, narratives, recommended_idx=2, week_date=week
        )

        rec = intel_svc.get_recommended_narrative(db_session, week_date=week)
        assert rec is not None
        assert rec.narrative_type == "alignment"
        assert rec.recommended_flag == 1


# ---------------------------------------------------------------------------
# SECTION 6 — Confidence Band Labels
# ---------------------------------------------------------------------------


class TestConfidenceBands:
    """Test confidence band label computation."""

    def test_struggling(self):
        assert "Struggling" in intel_svc.confidence_band_label(15)
        assert "Struggling" in intel_svc.confidence_band_label(0)
        assert "Struggling" in intel_svc.confidence_band_label(29)

    def test_mixed(self):
        assert "Mixed" in intel_svc.confidence_band_label(30)
        assert "Mixed" in intel_svc.confidence_band_label(45)
        assert "Mixed" in intel_svc.confidence_band_label(59)

    def test_strong(self):
        assert "Strong" in intel_svc.confidence_band_label(60)
        assert "Strong" in intel_svc.confidence_band_label(70)
        assert "Strong" in intel_svc.confidence_band_label(79)

    def test_clearly_working(self):
        assert "Clearly Working" in intel_svc.confidence_band_label(80)
        assert "Clearly Working" in intel_svc.confidence_band_label(95)
        assert "Clearly Working" in intel_svc.confidence_band_label(100)


# ---------------------------------------------------------------------------
# SECTION 7 — Integrated Intelligence Update
# ---------------------------------------------------------------------------


class TestIntelligenceUpdate:
    """Test the full integrated intelligence update pipeline."""

    def test_generate_intelligence_update(self, db_session):
        """Full pipeline generates all records."""
        # Create some task data
        theme = _create_theme(db_session)
        init = _create_initiative(db_session, theme=theme)
        c1 = _create_commitment(db_session, title="Build platform API")
        c2 = _create_commitment(db_session, title="Deploy infrastructure")
        _link_commitment_to_initiative(db_session, c1, init)
        _link_commitment_to_initiative(db_session, c2, init)
        _close_commitment(db_session, c1)

        result = intel_svc.generate_intelligence_update(
            db_session, send_email=False
        )

        # All components present
        assert result["update"] is not None
        assert result["strategic_narrative"] is not None
        assert result["confidence_history"] is not None
        assert len(result["weekly_narratives"]) == 3

        # Verify records in DB
        assert result["update"].confidence_score is not None
        assert result["confidence_history"].confidence_score == result["update"].confidence_score

    def test_intelligence_update_idempotent(self, db_session):
        """Running the pipeline twice doesn't create duplicates."""
        c = _create_commitment(db_session, title="Test task")

        r1 = intel_svc.generate_intelligence_update(
            db_session, send_email=False
        )
        r2 = intel_svc.generate_intelligence_update(
            db_session, send_email=False
        )

        # StrategicNarrative should be updated, not duplicated
        assert r1["strategic_narrative"].id == r2["strategic_narrative"].id

        # WeeklyNarratives should be updated, not duplicated
        for i in range(3):
            assert r1["weekly_narratives"][i].id == r2["weekly_narratives"][i].id

        # Verify counts
        week = intel_svc._week_start()
        narrative_count = (
            db_session.query(StrategicNarrative)
            .filter(StrategicNarrative.date == week)
            .count()
        )
        assert narrative_count == 1

        weekly_count = (
            db_session.query(WeeklyNarrative)
            .filter(WeeklyNarrative.week_date == week)
            .count()
        )
        assert weekly_count == 3

    def test_session_independence(self, db_session):
        """Data is loaded from DB, not session memory."""
        # Create data
        c = _create_commitment(db_session, title="Platform deployment")
        _close_commitment(db_session, c)

        # Generate update
        result = intel_svc.generate_intelligence_update(
            db_session, send_email=False
        )

        # Verify we can read all data back from DB
        narrative = intel_svc.get_strategic_narrative(db_session)
        assert narrative is not None
        assert narrative.narrative_summary is not None

        confidence = intel_svc.get_latest_confidence(db_session)
        assert confidence is not None

        weekly = intel_svc.get_weekly_narratives(db_session)
        assert len(weekly) == 3

        recommended = intel_svc.get_recommended_narrative(db_session)
        assert recommended is not None


# ---------------------------------------------------------------------------
# SECTION 8 — Email Composition
# ---------------------------------------------------------------------------


class TestEmailComposition:
    """Test email output format."""

    def test_compose_intelligence_email(self, db_session):
        """Email contains all required sections."""
        c = _create_commitment(db_session, title="Test task")

        result = intel_svc.generate_intelligence_update(
            db_session, send_email=False
        )

        email = intel_svc.compose_intelligence_email(
            result["update"],
            result["confidence_history"],
            result["weekly_narratives"],
            result["strategic_narrative"],
        )

        # Verify sections present
        assert "Brian," in email
        assert "NARRATIVE OPTION 1" in email
        assert "NARRATIVE OPTION 2" in email
        assert "NARRATIVE OPTION 3" in email
        assert "RECOMMENDED NARRATIVE" in email
        assert "STRATEGIC CONTINUITY ANALYSIS" in email
        assert "STRATEGY CONFIDENCE SIGNAL" in email
        assert "FORWARDABLE VERSION" in email
        assert "/100" in email  # Score format

    def test_email_includes_trend(self, db_session):
        """Email includes trend direction."""
        week1 = intel_svc._week_start() - timedelta(days=7)
        intel_svc._record_confidence_history(
            db_session, score=50, explanation="W1", week_date=week1
        )

        c = _create_commitment(db_session, title="Test task")
        result = intel_svc.generate_intelligence_update(
            db_session, send_email=False
        )

        email = intel_svc.compose_intelligence_email(
            result["update"],
            result["confidence_history"],
            result["weekly_narratives"],
            result["strategic_narrative"],
        )

        # Should include trend indicator
        assert any(
            t in email for t in ["(improving)", "(declining)", "(flat)"]
        )

    def test_email_includes_band_label(self, db_session):
        """Email includes confidence band label."""
        c = _create_commitment(db_session, title="Test task")
        result = intel_svc.generate_intelligence_update(
            db_session, send_email=False
        )

        email = intel_svc.compose_intelligence_email(
            result["update"],
            result["confidence_history"],
            result["weekly_narratives"],
            result["strategic_narrative"],
        )

        assert "Band:" in email


# ---------------------------------------------------------------------------
# SECTION 9 — API Endpoints
# ---------------------------------------------------------------------------


class TestAPIEndpoints:
    """Test Feature 022 API endpoints."""

    def test_post_intelligence_generate(self, client):
        """POST /intelligence/generate creates all records."""
        # Create a task first
        client.post(
            "/commitments/open",
            json={"title": "Test platform build"},
            headers=HEADERS,
        )

        resp = client.post("/intelligence/generate", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()

        assert data["update"] is not None
        assert data["strategic_narrative"] is not None
        assert data["confidence_history"] is not None
        assert len(data["weekly_narratives"]) == 3

    def test_get_contribution_notes(self, client):
        """GET /intelligence/contribution-notes returns notes."""
        # Open a task (triggers contribution note)
        client.post(
            "/commitments/open",
            json={"title": "Deploy infrastructure"},
            headers=HEADERS,
        )

        resp = client.get("/intelligence/contribution-notes", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["strategic_contribution_note"]

    def test_get_impact_notes(self, client):
        """GET /intelligence/impact-notes returns notes."""
        # Open and close a task
        open_resp = client.post(
            "/commitments/open",
            json={"title": "Deploy platform API"},
            headers=HEADERS,
        )
        cid = open_resp.json()["id"]
        client.post(
            "/commitments/close",
            json={"commitment_id": cid},
            headers=HEADERS,
        )

        resp = client.get("/intelligence/impact-notes", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_get_unclear_contributions(self, client):
        """GET /intelligence/unclear-contributions returns unclear notes."""
        client.post(
            "/commitments/open",
            json={"title": "Fix random bug"},
            headers=HEADERS,
        )

        resp = client.get(
            "/intelligence/unclear-contributions", headers=HEADERS
        )
        assert resp.status_code == 200

    def test_patch_confirm_contribution(self, client):
        """PATCH /intelligence/contribution-notes/{id} confirms a note."""
        # Open a task with unclear contribution
        client.post(
            "/commitments/open",
            json={"title": "Fix random bug"},
            headers=HEADERS,
        )

        # Get the note
        notes_resp = client.get(
            "/intelligence/contribution-notes", headers=HEADERS
        )
        notes = notes_resp.json()
        assert len(notes) >= 1
        note_id = notes[0]["id"]

        # Confirm it
        resp = client.patch(
            f"/intelligence/contribution-notes/{note_id}",
            json={"updated_text": "This supports the CI initiative."},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["source"] == "user_confirmed"

    def test_get_narratives(self, client):
        """GET /intelligence/narratives returns strategic narratives."""
        # Generate first
        client.post("/intelligence/generate", headers=HEADERS)

        resp = client.get("/intelligence/narratives", headers=HEADERS)
        assert resp.status_code == 200

    def test_get_confidence_history(self, client):
        """GET /intelligence/confidence-history returns history."""
        client.post("/intelligence/generate", headers=HEADERS)

        resp = client.get(
            "/intelligence/confidence-history", headers=HEADERS
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert "confidence_score" in data[0]
        assert "band_label" in data[0]

    def test_get_confidence_latest(self, client):
        """GET /intelligence/confidence-latest returns latest score."""
        client.post("/intelligence/generate", headers=HEADERS)

        resp = client.get(
            "/intelligence/confidence-latest", headers=HEADERS
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "confidence_score" in data
        assert "trend_direction" in data
        assert "band_label" in data

    def test_get_weekly_narratives(self, client):
        """GET /intelligence/weekly-narratives returns 3 drafts."""
        client.post("/intelligence/generate", headers=HEADERS)

        resp = client.get(
            "/intelligence/weekly-narratives", headers=HEADERS
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    def test_get_recommended_narrative(self, client):
        """GET /intelligence/recommended-narrative returns recommended."""
        client.post("/intelligence/generate", headers=HEADERS)

        resp = client.get(
            "/intelligence/recommended-narrative", headers=HEADERS
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["recommended_flag"] is True

    def test_open_commitment_creates_contribution_note(self, client):
        """Opening a commitment via API also creates a contribution note."""
        resp = client.post(
            "/commitments/open",
            json={"title": "Build new platform capability"},
            headers=HEADERS,
        )
        assert resp.status_code == 200

        notes_resp = client.get(
            "/intelligence/contribution-notes", headers=HEADERS
        )
        notes = notes_resp.json()
        assert len(notes) >= 1
        assert any("platform" in n["strategic_contribution_note"].lower() or "capability" in n["strategic_contribution_note"].lower() for n in notes)

    def test_close_commitment_creates_impact_note(self, client):
        """Closing a commitment via API also creates an impact note."""
        open_resp = client.post(
            "/commitments/open",
            json={"title": "Deploy infrastructure pipeline"},
            headers=HEADERS,
        )
        cid = open_resp.json()["id"]

        client.post(
            "/commitments/close",
            json={"commitment_id": cid},
            headers=HEADERS,
        )

        notes_resp = client.get(
            "/intelligence/impact-notes", headers=HEADERS
        )
        notes = notes_resp.json()
        assert len(notes) >= 1


# ---------------------------------------------------------------------------
# SECTION 10 — Scheduler Setup
# ---------------------------------------------------------------------------


class TestScheduler:
    """Test APScheduler configuration."""

    def test_setup_scheduler(self, db_session):
        """Scheduler can be set up and returns a scheduler instance."""

        def _get_db():
            yield db_session

        scheduler = intel_svc.setup_scheduler(_get_db)
        assert scheduler is not None

        # Verify job registered
        job = scheduler.get_job("friday_intelligence_update")
        assert job is not None
        assert "Friday" in job.name

        scheduler.shutdown(wait=False)

    def test_scheduler_without_apscheduler(self, db_session, monkeypatch):
        """Graceful handling when APScheduler is not installed."""
        import importlib

        # Monkeypatch the import to simulate missing package
        original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

        def mock_import(name, *args, **kwargs):
            if "apscheduler" in name:
                raise ImportError("No module named 'apscheduler'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        def _get_db():
            yield db_session

        result = intel_svc.setup_scheduler(_get_db)
        assert result is None


# ---------------------------------------------------------------------------
# SECTION 11 — Weekly Review Sessions
# ---------------------------------------------------------------------------


class TestReviewSessions:
    """Test ChatGPT review session creation and management."""

    def test_create_review_session(self, db_session):
        """Create a new review session for the current week."""
        now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)  # Friday
        week_date = intel_svc._week_start(now)

        session = intel_svc._ensure_review_session(db_session, week_date)

        assert session is not None
        # SQLite strips timezone info, so compare naive datetimes
        assert session.week_date.replace(tzinfo=None) == week_date.replace(tzinfo=None)
        assert "AI Platform Weekly Memo Review" in session.session_title
        assert session.status == "open"
        assert session.chatgpt_session_link is None

    def test_review_session_idempotent(self, db_session):
        """Creating session for same week returns the same record."""
        now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)
        week_date = intel_svc._week_start(now)

        session1 = intel_svc._ensure_review_session(db_session, week_date)
        session2 = intel_svc._ensure_review_session(db_session, week_date)

        assert str(session1.id) == str(session2.id)
        # Only one record in DB
        count = db_session.query(WeeklyReviewSession).count()
        assert count == 1

    def test_review_session_with_link(self, db_session):
        """Create session with a ChatGPT session link."""
        now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)
        week_date = intel_svc._week_start(now)

        session = intel_svc._ensure_review_session(
            db_session, week_date,
            chatgpt_session_link="https://chatgpt.com/session/abc123",
        )

        assert session.chatgpt_session_link == "https://chatgpt.com/session/abc123"

    def test_review_session_different_weeks(self, db_session):
        """Different weeks create different sessions."""
        week1 = datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc)
        week2 = datetime(2026, 3, 16, 0, 0, tzinfo=timezone.utc)

        s1 = intel_svc._ensure_review_session(db_session, week1)
        s2 = intel_svc._ensure_review_session(db_session, week2)

        assert str(s1.id) != str(s2.id)
        count = db_session.query(WeeklyReviewSession).count()
        assert count == 2

    def test_get_review_session(self, db_session):
        """Get review session for a specific week."""
        now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)
        week_date = intel_svc._week_start(now)

        intel_svc._ensure_review_session(db_session, week_date)
        result = intel_svc.get_review_session(db_session, week_date)

        assert result is not None
        assert result.week_date.replace(tzinfo=None) == week_date.replace(tzinfo=None)

    def test_get_review_session_not_found(self, db_session):
        """Returns None when no session exists for the week."""
        week_date = datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc)
        result = intel_svc.get_review_session(db_session, week_date)
        assert result is None

    def test_list_review_sessions(self, db_session):
        """List recent review sessions."""
        week1 = datetime(2026, 3, 2, 0, 0, tzinfo=timezone.utc)
        week2 = datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc)
        week3 = datetime(2026, 3, 16, 0, 0, tzinfo=timezone.utc)

        intel_svc._ensure_review_session(db_session, week1)
        intel_svc._ensure_review_session(db_session, week2)
        intel_svc._ensure_review_session(db_session, week3)

        sessions = intel_svc.list_review_sessions(db_session, limit=10)
        assert len(sessions) == 3
        # Most recent first
        assert sessions[0].week_date.replace(tzinfo=None) == week3.replace(tzinfo=None)

    def test_update_review_session(self, db_session):
        """Update a review session with link and status."""
        now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)
        week_date = intel_svc._week_start(now)
        session = intel_svc._ensure_review_session(db_session, week_date)

        updated = intel_svc.update_review_session(
            db_session, str(session.id),
            chatgpt_session_link="https://chatgpt.com/session/xyz",
            status="finalized",
        )

        assert updated is not None
        assert updated.chatgpt_session_link == "https://chatgpt.com/session/xyz"
        assert updated.status == "finalized"

    def test_update_review_session_not_found(self, db_session):
        """Returns None when session doesn't exist."""
        result = intel_svc.update_review_session(
            db_session, str(uuid.uuid4()),
            chatgpt_session_link="https://chatgpt.com/session/xyz",
        )
        assert result is None

    def test_finalize_review_session(self, db_session):
        """Finalize the review session for a week."""
        now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)
        week_date = intel_svc._week_start(now)
        intel_svc._ensure_review_session(db_session, week_date)

        result = intel_svc.finalize_review_session(db_session, week_date)

        assert result is not None
        assert result.status == "finalized"

    def test_finalize_review_session_not_found(self, db_session):
        """Returns None when no session to finalize."""
        week_date = datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc)
        result = intel_svc.finalize_review_session(db_session, week_date)
        assert result is None

    def test_session_title_format(self, db_session):
        """Session title matches required format."""
        week_date = datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc)
        session = intel_svc._ensure_review_session(db_session, week_date)

        assert session.session_title == "AI Platform Weekly Memo Review — 2026-03-09"


# ---------------------------------------------------------------------------
# SECTION 12 — Strategy Debrief Records
# ---------------------------------------------------------------------------


class TestStrategyDebrief:
    """Test strategy debrief question/answer recording."""

    def test_create_debrief_record(self, db_session):
        """Create a debrief record with a question."""
        now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)
        record = intel_svc.create_debrief_record(
            db_session,
            "What progress this week most meaningfully advanced the platform objective?",
            now=now,
        )

        assert record is not None
        assert record.question == "What progress this week most meaningfully advanced the platform objective?"
        assert record.response is None
        assert record.derived_insight is None

    def test_create_debrief_with_response(self, db_session):
        """Create a debrief record with question and response."""
        now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)
        record = intel_svc.create_debrief_record(
            db_session,
            "Where do you believe we made less progress than expected?",
            response="The knowledge layer pipeline stalled.",
            derived_insight="Need to reprioritize knowledge layer resources.",
            now=now,
        )

        assert record.response == "The knowledge layer pipeline stalled."
        assert record.derived_insight == "Need to reprioritize knowledge layer resources."

    def test_debrief_record_idempotent(self, db_session):
        """Same question for same week updates rather than duplicates."""
        now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)
        question = "What should the team feel most momentum about right now?"

        r1 = intel_svc.create_debrief_record(
            db_session, question, now=now,
        )
        r2 = intel_svc.create_debrief_record(
            db_session, question,
            response="Agent deployment pipeline is working.",
            now=now,
        )

        assert str(r1.id) == str(r2.id)
        assert r2.response == "Agent deployment pipeline is working."
        count = db_session.query(StrategyDebriefRecord).count()
        assert count == 1

    def test_update_debrief_record(self, db_session):
        """Update a debrief record with Brian's response."""
        now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)
        record = intel_svc.create_debrief_record(
            db_session, "Test question?", now=now,
        )

        updated = intel_svc.update_debrief_record(
            db_session, str(record.id),
            response="Updated response.",
            derived_insight="Key insight derived.",
        )

        assert updated is not None
        assert updated.response == "Updated response."
        assert updated.derived_insight == "Key insight derived."

    def test_update_debrief_record_not_found(self, db_session):
        """Returns None when record doesn't exist."""
        result = intel_svc.update_debrief_record(
            db_session, str(uuid.uuid4()),
            response="Not found",
        )
        assert result is None

    def test_get_debrief_records(self, db_session):
        """Get all debrief records for a given week."""
        now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)
        week_date = intel_svc._week_start(now)

        intel_svc.create_debrief_record(
            db_session, "Question 1?", now=now,
        )
        intel_svc.create_debrief_record(
            db_session, "Question 2?", now=now,
        )

        records = intel_svc.get_debrief_records(db_session, week_date)
        assert len(records) == 2

    def test_debrief_records_ordered_by_recorded_at(self, db_session):
        """Records returned in chronological order."""
        t1 = datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 3, 13, 11, 0, tzinfo=timezone.utc)

        intel_svc.create_debrief_record(
            db_session, "First question?", now=t1,
        )
        intel_svc.create_debrief_record(
            db_session, "Second question?", now=t2,
        )

        week_date = intel_svc._week_start(t1)
        records = intel_svc.get_debrief_records(db_session, week_date)

        assert records[0].question == "First question?"
        assert records[1].question == "Second question?"

    def test_seed_debrief_questions(self, db_session):
        """Seed the default 4 debrief questions for the week."""
        now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)

        records = intel_svc.seed_debrief_questions(db_session, now=now)

        assert len(records) == 4
        questions = [r.question for r in records]
        assert "What progress this week most meaningfully advanced the platform objective?" in questions
        assert "Where do you believe we made less progress than expected?" in questions
        assert "Is there a signal that our strategy might need adjustment?" in questions
        assert "What should the team feel most momentum about right now?" in questions

    def test_seed_debrief_idempotent(self, db_session):
        """Seeding twice doesn't create duplicates."""
        now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)

        r1 = intel_svc.seed_debrief_questions(db_session, now=now)
        r2 = intel_svc.seed_debrief_questions(db_session, now=now)

        assert len(r1) == 4
        assert len(r2) == 4
        count = db_session.query(StrategyDebriefRecord).count()
        assert count == 4

    def test_debrief_different_weeks(self, db_session):
        """Different weeks have separate debrief records."""
        t1 = datetime(2026, 3, 6, 12, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)

        intel_svc.seed_debrief_questions(db_session, now=t1)
        intel_svc.seed_debrief_questions(db_session, now=t2)

        count = db_session.query(StrategyDebriefRecord).count()
        assert count == 8  # 4 per week


# ---------------------------------------------------------------------------
# SECTION 13 — Review Session Initialization Data
# ---------------------------------------------------------------------------


class TestReviewSessionInitData:
    """Test the initialization data payload for ChatGPT sessions."""

    def test_init_data_structure(self, db_session):
        """Initialization data has the expected keys."""
        week_date = datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc)
        data = intel_svc.get_review_session_initialization_data(
            db_session, week_date,
        )

        assert "strategic_objective" in data
        assert "debrief_questions" in data
        assert "opening_message" in data
        assert "narrative_options" in data
        assert "confidence_score" in data
        assert "strategic_narrative" in data
        assert "recommended_narrative" in data

    def test_init_data_debrief_questions(self, db_session):
        """Initialization data includes the default debrief questions."""
        week_date = datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc)
        data = intel_svc.get_review_session_initialization_data(
            db_session, week_date,
        )

        assert len(data["debrief_questions"]) == 4
        assert "What progress this week" in data["debrief_questions"][0]

    def test_init_data_opening_message(self, db_session):
        """Opening message matches the spec."""
        week_date = datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc)
        data = intel_svc.get_review_session_initialization_data(
            db_session, week_date,
        )

        assert "three narrative drafts" in data["opening_message"]
        assert "Let's refine this together" in data["opening_message"]


# ---------------------------------------------------------------------------
# SECTION 14 — Email Composition with Review Session
# ---------------------------------------------------------------------------


class TestEmailWithReviewSession:
    """Test email composition includes review session section."""

    def _make_update_and_deps(self, db_session):
        """Helper to create update + confidence + narrative + session."""
        now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)
        week_date = intel_svc._week_start(now)

        update = WeeklyStrategyUpdate(
            id=uuid.uuid4(),
            week_start_date=week_date,
            narrative_options=json.dumps([
                {
                    "framing": "Execution Progress",
                    "strategic_objective": "Drive AI platform adoption",
                    "why": "Shows progress",
                    "behavior": "Keep shipping",
                    "body": "This week the team delivered..."
                },
            ]),
            recommended_narrative=0,
            narrative_continuity="Continuing to build",
            confidence_score=72,
            confidence_explanation="Strong execution signals",
            forwardable_body="Team update: great week.",
            score_components=json.dumps({"execution": 80, "momentum": 70, "alignment": 65, "friction": 30}),
        )
        db_session.add(update)

        confidence = StrategyConfidenceHistory(
            id=uuid.uuid4(),
            date=week_date,
            confidence_score=72,
            previous_score=65,
            trend_direction="improving",
            confidence_explanation="Strong execution signals",
        )
        db_session.add(confidence)

        narrative = StrategicNarrative(
            id=uuid.uuid4(),
            date=week_date,
            narrative_summary="Momentum building across platform.",
            strategic_objective="Drive AI platform adoption",
        )
        db_session.add(narrative)

        session = intel_svc._ensure_review_session(
            db_session, week_date,
            chatgpt_session_link="https://chatgpt.com/session/test123",
        )

        db_session.commit()
        return update, confidence, narrative, session

    def test_email_includes_review_session_section(self, db_session):
        """Email includes ChatGPT Review Session section."""
        update, confidence, narrative, session = self._make_update_and_deps(db_session)

        email = intel_svc.compose_intelligence_email(
            update, confidence, [], narrative, review_session=session,
        )

        assert "--- CHATGPT REVIEW SESSION ---" in email
        assert "AI Platform Weekly Memo Review" in email
        assert "https://chatgpt.com/session/test123" in email

    def test_email_includes_debrief_questions(self, db_session):
        """Email includes debrief questions when review session present."""
        update, confidence, narrative, session = self._make_update_and_deps(db_session)

        email = intel_svc.compose_intelligence_email(
            update, confidence, [], narrative, review_session=session,
        )

        assert "Strategy Debrief" in email
        assert "What progress this week" in email
        assert "less progress than expected" in email

    def test_email_without_review_session(self, db_session):
        """Email omits review session section when not provided."""
        update, confidence, narrative, _ = self._make_update_and_deps(db_session)

        email = intel_svc.compose_intelligence_email(
            update, confidence, [], narrative,
        )

        assert "--- CHATGPT REVIEW SESSION ---" not in email


# ---------------------------------------------------------------------------
# SECTION 15 — Review Session & Debrief API Endpoints
# ---------------------------------------------------------------------------


class TestReviewSessionEndpoints:
    """Test API endpoints for review sessions and debrief."""

    def test_post_create_review_session(self, client):
        """POST /intelligence/review-sessions creates a session."""
        resp = client.post(
            "/intelligence/review-sessions",
            json={},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "AI Platform Weekly Memo Review" in data["session_title"]
        assert data["status"] == "open"

    def test_post_create_review_session_idempotent(self, client):
        """POST same week returns same session."""
        r1 = client.post(
            "/intelligence/review-sessions",
            json={},
            headers=HEADERS,
        )
        r2 = client.post(
            "/intelligence/review-sessions",
            json={},
            headers=HEADERS,
        )
        assert r1.json()["id"] == r2.json()["id"]

    def test_get_list_review_sessions(self, client):
        """GET /intelligence/review-sessions lists sessions."""
        # Create one first
        client.post(
            "/intelligence/review-sessions",
            json={},
            headers=HEADERS,
        )
        resp = client.get(
            "/intelligence/review-sessions",
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_get_current_review_session(self, client):
        """GET /intelligence/review-sessions/current returns current session."""
        client.post(
            "/intelligence/review-sessions",
            json={},
            headers=HEADERS,
        )
        resp = client.get(
            "/intelligence/review-sessions/current",
            headers=HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "open"

    def test_get_current_review_session_not_found(self, client):
        """GET /intelligence/review-sessions/current returns 404 if none."""
        resp = client.get(
            "/intelligence/review-sessions/current",
            headers=HEADERS,
        )
        assert resp.status_code == 404

    def test_patch_update_review_session(self, client):
        """PATCH /intelligence/review-sessions/{id} updates session."""
        create_resp = client.post(
            "/intelligence/review-sessions",
            json={},
            headers=HEADERS,
        )
        session_id = create_resp.json()["id"]

        resp = client.patch(
            f"/intelligence/review-sessions/{session_id}",
            json={"chatgpt_session_link": "https://chatgpt.com/test", "status": "finalized"},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["chatgpt_session_link"] == "https://chatgpt.com/test"
        assert data["status"] == "finalized"

    def test_post_finalize_review_session(self, client):
        """POST /intelligence/review-sessions/finalize marks session finalized."""
        client.post(
            "/intelligence/review-sessions",
            json={},
            headers=HEADERS,
        )
        resp = client.post(
            "/intelligence/review-sessions/finalize",
            headers=HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "finalized"

    def test_get_init_data(self, client):
        """GET /intelligence/review-sessions/init-data returns structured data."""
        resp = client.get(
            "/intelligence/review-sessions/init-data",
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "strategic_objective" in data
        assert "debrief_questions" in data
        assert len(data["debrief_questions"]) == 4

    def test_post_create_debrief(self, client):
        """POST /intelligence/debrief creates a debrief record."""
        resp = client.post(
            "/intelligence/debrief",
            json={"question": "What went well this week?"},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["question"] == "What went well this week?"
        assert data["response"] is None

    def test_post_create_debrief_with_response(self, client):
        """POST /intelligence/debrief with response and insight."""
        resp = client.post(
            "/intelligence/debrief",
            json={
                "question": "What went well?",
                "response": "Agent deployment pipeline is strong.",
                "derived_insight": "Keep investing in agent infra.",
            },
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["response"] == "Agent deployment pipeline is strong."
        assert data["derived_insight"] == "Keep investing in agent infra."

    def test_get_list_debrief(self, client):
        """GET /intelligence/debrief lists records for current week."""
        client.post(
            "/intelligence/debrief",
            json={"question": "Q1?"},
            headers=HEADERS,
        )
        client.post(
            "/intelligence/debrief",
            json={"question": "Q2?"},
            headers=HEADERS,
        )
        resp = client.get(
            "/intelligence/debrief",
            headers=HEADERS,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_patch_update_debrief(self, client):
        """PATCH /intelligence/debrief/{id} updates response."""
        create_resp = client.post(
            "/intelligence/debrief",
            json={"question": "Test?"},
            headers=HEADERS,
        )
        record_id = create_resp.json()["id"]

        resp = client.patch(
            f"/intelligence/debrief/{record_id}",
            json={"response": "My answer.", "derived_insight": "Key finding."},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["response"] == "My answer."
        assert data["derived_insight"] == "Key finding."

    def test_patch_update_debrief_not_found(self, client):
        """PATCH /intelligence/debrief/{id} returns 404 for missing record."""
        resp = client.patch(
            f"/intelligence/debrief/{uuid.uuid4()}",
            json={"response": "Not found"},
            headers=HEADERS,
        )
        assert resp.status_code == 404

    def test_post_seed_debrief(self, client):
        """POST /intelligence/debrief/seed seeds default questions."""
        resp = client.post(
            "/intelligence/debrief/seed",
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4

    def test_seed_debrief_idempotent(self, client):
        """POST /intelligence/debrief/seed twice doesn't duplicate."""
        client.post("/intelligence/debrief/seed", headers=HEADERS)
        resp = client.post("/intelligence/debrief/seed", headers=HEADERS)
        assert resp.status_code == 200
        assert len(resp.json()) == 4

        list_resp = client.get("/intelligence/debrief", headers=HEADERS)
        assert len(list_resp.json()) == 4
