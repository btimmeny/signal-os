"""Tests for Feature 020 — Friday Strategic Execution Update System."""

import json
import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import HEADERS


# ---------------------------------------------------------------------------
# Helper: seed test data
# ---------------------------------------------------------------------------

def _seed_initiative(client, title="Test Initiative"):
    """Create an initiative and return its ID."""
    resp = client.post(
        "/initiatives/create",
        json={"title": title},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


def _seed_commitment(client, title="Test Task", urgency="NOW", due_at=None, priority_order=None):
    """Create a commitment and return its ID."""
    body = {"title": title, "urgency": urgency}
    if due_at:
        body["due_at"] = due_at
    if priority_order:
        body["priority_order"] = priority_order
    resp = client.post(
        "/commitments/open",
        json=body,
        headers=HEADERS,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


def _close_commitment(client, commitment_id):
    """Close a commitment."""
    resp = client.post(
        "/commitments/close",
        json={"commitment_id": commitment_id},
        headers=HEADERS,
    )
    assert resp.status_code == 200


def _link_to_initiative(client, initiative_id, commitment_id):
    """Link a commitment to an initiative."""
    resp = client.post(
        "/initiatives/link",
        json={"initiative_id": initiative_id, "commitment_id": commitment_id},
        headers=HEADERS,
    )
    assert resp.status_code == 200


def _seed_theme(client, title="Test Theme"):
    """Create a strategic theme and return its ID."""
    resp = client.post(
        "/themes/create",
        json={"title": title},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


def _seed_rich_data(client):
    """Seed a realistic dataset with initiatives, tasks, themes, and links."""
    # Create themes
    t1 = _seed_theme(client, "AI Platform Architecture")
    t2 = _seed_theme(client, "Enterprise Integration")

    # Create initiatives
    i1 = _seed_initiative(client, "Build Claude CLI integration")
    i2 = _seed_initiative(client, "API gateway modernization")
    i3 = _seed_initiative(client, "Knowledge layer design")

    # Create tasks with priorities
    c1 = _seed_commitment(client, "Launch Claude CLI beta", urgency="NOW", priority_order=1)
    c2 = _seed_commitment(client, "Design API rate limiting", urgency="SOON", priority_order=2)
    c3 = _seed_commitment(client, "Write knowledge graph spec", urgency="SCHEDULED")
    c4 = _seed_commitment(client, "Review architecture docs", urgency="ADMIN")
    c5 = _seed_commitment(client, "Deploy monitoring dashboard", urgency="NOW", priority_order=3)

    # Create a task with a due date in the past (overdue)
    overdue_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    c6 = _seed_commitment(client, "Submit compliance report", urgency="SOON", due_at=overdue_date)

    # Create a task with a due date in the next 7 days
    soon_date = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    c7 = _seed_commitment(client, "Present to leadership", urgency="NOW", due_at=soon_date)

    # Link tasks to initiatives
    _link_to_initiative(client, i1, c1)
    _link_to_initiative(client, i1, c5)
    _link_to_initiative(client, i2, c2)
    _link_to_initiative(client, i3, c3)

    # Close some tasks (simulates execution this week)
    c_done1 = _seed_commitment(client, "Finalize CLI architecture", urgency="NOW")
    _link_to_initiative(client, i1, c_done1)
    _close_commitment(client, c_done1)

    c_done2 = _seed_commitment(client, "Complete API auth spec", urgency="SOON")
    _link_to_initiative(client, i2, c_done2)
    _close_commitment(client, c_done2)

    c_done3 = _seed_commitment(client, "Draft knowledge layer RFC", urgency="SCHEDULED")
    _close_commitment(client, c_done3)

    return {
        "themes": [t1, t2],
        "initiatives": [i1, i2, i3],
        "open_tasks": [c1, c2, c3, c4, c5, c6, c7],
        "closed_tasks": [c_done1, c_done2, c_done3],
    }


# ---------------------------------------------------------------------------
# Signal Extraction Tests
# ---------------------------------------------------------------------------

class TestSignalExtraction:
    """Tests for the signal extraction pipeline."""

    def test_extract_signals_empty_db(self, client, db_session):
        """Signal extraction works with an empty database."""
        from app.services.friday_update import extract_signals
        signals = extract_signals(db_session)

        assert signals["commitments_closed"] == []
        assert signals["commitments_opened"] == []
        assert signals["total_open"] == []
        assert signals["overdue"] == []
        assert signals["due_soon"] == []
        assert signals["active_initiatives"] == []
        assert signals["completed_initiatives"] == []
        assert signals["stalled_initiatives"] == []
        assert signals["active_themes"] == []
        assert "extraction_date" in signals

    def test_extract_signals_with_data(self, client, db_session):
        """Signal extraction captures open, closed, overdue, and due-soon tasks."""
        data = _seed_rich_data(client)
        from app.services.friday_update import extract_signals
        signals = extract_signals(db_session)

        # Should have open tasks
        assert len(signals["total_open"]) == 7

        # Should have closed tasks (recently closed)
        assert len(signals["commitments_closed"]) == 3

        # Should have overdue tasks
        assert len(signals["overdue"]) >= 1
        overdue_titles = [o["title"] for o in signals["overdue"]]
        assert "Submit compliance report" in overdue_titles

        # Should have due-soon tasks
        assert len(signals["due_soon"]) >= 1
        due_titles = [d["title"] for d in signals["due_soon"]]
        assert "Present to leadership" in due_titles

        # Should have active initiatives
        assert len(signals["active_initiatives"]) == 3

        # Should have active themes
        assert len(signals["active_themes"]) == 2

        # Should have priorities
        assert len(signals["priorities"]) >= 3
        assert signals["priorities"][0]["priority_order"] == 1

    def test_extract_signals_initiative_movement(self, client, db_session):
        """Signal extraction detects which initiatives had task closures."""
        data = _seed_rich_data(client)
        from app.services.friday_update import extract_signals
        signals = extract_signals(db_session)

        # Initiatives with closures should show tasks_closed_this_week > 0
        moving = [
            i for i in signals["active_initiatives"]
            if i["tasks_closed_this_week"] > 0
        ]
        assert len(moving) >= 1

    def test_extract_signals_stalled_initiatives(self, client, db_session):
        """Signal extraction identifies stalled initiatives (open tasks but no closures)."""
        # Create an initiative with tasks but no closures
        init_id = _seed_initiative(client, "Stalled Project")
        task_id = _seed_commitment(client, "Stalled task")
        _link_to_initiative(client, init_id, task_id)

        from app.services.friday_update import extract_signals
        signals = extract_signals(db_session)

        stalled_titles = [s["title"] for s in signals["stalled_initiatives"]]
        assert "Stalled Project" in stalled_titles


# ---------------------------------------------------------------------------
# Confidence Score Tests
# ---------------------------------------------------------------------------

class TestConfidenceScore:
    """Tests for the Strategy Confidence Score algorithm."""

    def test_score_range(self, client, db_session):
        """Score is always between 0 and 100."""
        from app.services.friday_update import extract_signals, _compute_confidence_score

        # Empty DB
        signals = extract_signals(db_session)
        result = _compute_confidence_score(signals)
        assert 0 <= result["score"] <= 100

        # With data
        _seed_rich_data(client)
        signals = extract_signals(db_session)
        result = _compute_confidence_score(signals)
        assert 0 <= result["score"] <= 100

    def test_score_components(self, client, db_session):
        """Score includes all four components."""
        _seed_rich_data(client)
        from app.services.friday_update import extract_signals, _compute_confidence_score
        signals = extract_signals(db_session)
        result = _compute_confidence_score(signals)

        assert "execution" in result["components"]
        assert "momentum" in result["components"]
        assert "alignment" in result["components"]
        assert "friction" in result["components"]

        for key in ("execution", "momentum", "alignment", "friction"):
            assert 0 <= result["components"][key] <= 100

    def test_score_explanation_not_empty(self, client, db_session):
        """Score includes a non-empty explanation."""
        _seed_rich_data(client)
        from app.services.friday_update import extract_signals, _compute_confidence_score
        signals = extract_signals(db_session)
        result = _compute_confidence_score(signals)
        assert len(result["explanation"]) > 10

    def test_higher_score_with_more_closures(self, client, db_session):
        """More task closures should increase the execution component."""
        from app.services.friday_update import _compute_confidence_score

        # Scenario A: No closures, many open tasks
        signals_low = {
            "commitments_closed": [],
            "commitments_opened": [],
            "total_open": [{"id": "1", "title": "t", "status": "OPEN", "urgency": "NOW"}] * 10,
            "overdue": [],
            "due_soon": [],
            "active_initiatives": [],
            "completed_initiatives": [],
            "stalled_initiatives": [],
            "active_themes": [],
            "recent_comments": [],
            "priorities": [],
        }

        # Scenario B: Many closures
        signals_high = dict(signals_low)
        signals_high["commitments_closed"] = [{"id": str(i), "title": f"t{i}", "closed_at": "2026-03-01"} for i in range(5)]

        result_low = _compute_confidence_score(signals_low)
        result_high = _compute_confidence_score(signals_high)

        assert result_high["components"]["execution"] > result_low["components"]["execution"]

    def test_friction_reduces_with_overdue(self, client, db_session):
        """Overdue tasks should reduce the friction component score."""
        from app.services.friday_update import _compute_confidence_score

        signals_clean = {
            "commitments_closed": [],
            "commitments_opened": [],
            "total_open": [{"id": "1", "title": "t", "status": "OPEN", "urgency": "NOW"}] * 5,
            "overdue": [],
            "due_soon": [],
            "active_initiatives": [],
            "completed_initiatives": [],
            "stalled_initiatives": [],
            "active_themes": [],
            "recent_comments": [],
            "priorities": [],
        }

        signals_overdue = dict(signals_clean)
        signals_overdue["overdue"] = [{"id": str(i), "title": f"t{i}", "due_at": "2026-03-01"} for i in range(3)]

        result_clean = _compute_confidence_score(signals_clean)
        result_overdue = _compute_confidence_score(signals_overdue)

        assert result_overdue["components"]["friction"] < result_clean["components"]["friction"]


# ---------------------------------------------------------------------------
# Narrative Generation Tests
# ---------------------------------------------------------------------------

class TestNarrativeGeneration:
    """Tests for the three strategic narrative drafts."""

    def test_three_narratives_generated(self, client, db_session):
        """Exactly three narrative options are generated."""
        _seed_rich_data(client)
        from app.services.friday_update import extract_signals, generate_narratives
        signals = extract_signals(db_session)
        narratives = generate_narratives(signals)
        assert len(narratives) == 3

    def test_narrative_framings(self, client, db_session):
        """Each narrative has a distinct framing name."""
        _seed_rich_data(client)
        from app.services.friday_update import extract_signals, generate_narratives
        signals = extract_signals(db_session)
        narratives = generate_narratives(signals)

        framings = [n["framing"] for n in narratives]
        assert "Execution Progress" in framings
        assert "Momentum" in framings
        assert "Alignment" in framings

    def test_narrative_structure(self, client, db_session):
        """Each narrative has required fields: framing, strategic_objective, why, behavior, body."""
        _seed_rich_data(client)
        from app.services.friday_update import extract_signals, generate_narratives
        signals = extract_signals(db_session)
        narratives = generate_narratives(signals)

        for narrative in narratives:
            assert "framing" in narrative
            assert "strategic_objective" in narrative
            assert "why" in narrative
            assert "behavior" in narrative
            assert "body" in narrative

            # Each field should be non-empty
            assert len(narrative["framing"]) > 0
            assert len(narrative["strategic_objective"]) > 10
            assert len(narrative["why"]) > 10
            assert len(narrative["behavior"]) > 10
            assert len(narrative["body"]) > 50

    def test_narrative_no_bullet_lists(self, client, db_session):
        """Narratives must be prose paragraphs — no bullet lists."""
        _seed_rich_data(client)
        from app.services.friday_update import extract_signals, generate_narratives
        signals = extract_signals(db_session)
        narratives = generate_narratives(signals)

        for narrative in narratives:
            body = narrative["body"]
            # Should not contain bullet list markers
            lines = body.split("\n")
            for line in lines:
                stripped = line.strip()
                if stripped:
                    assert not stripped.startswith("- "), f"Bullet list found in {narrative['framing']}: {stripped}"
                    assert not stripped.startswith("* "), f"Bullet list found in {narrative['framing']}: {stripped}"
                    assert not re.match(r"^\d+\.\s", stripped), f"Numbered list found in {narrative['framing']}: {stripped}"

    def test_narrative_three_paragraphs(self, client, db_session):
        """Each narrative body should have approximately 3 paragraphs."""
        _seed_rich_data(client)
        from app.services.friday_update import extract_signals, generate_narratives
        signals = extract_signals(db_session)
        narratives = generate_narratives(signals)

        for narrative in narratives:
            paragraphs = [p.strip() for p in narrative["body"].split("\n\n") if p.strip()]
            assert len(paragraphs) == 3, (
                f"{narrative['framing']} has {len(paragraphs)} paragraphs, expected 3"
            )

    def test_narrative_word_count(self, client, db_session):
        """Each narrative body should be roughly 100-300 words (flexible range)."""
        _seed_rich_data(client)
        from app.services.friday_update import extract_signals, generate_narratives
        signals = extract_signals(db_session)
        narratives = generate_narratives(signals)

        for narrative in narratives:
            word_count = len(narrative["body"].split())
            assert 50 < word_count < 400, (
                f"{narrative['framing']} has {word_count} words, expected 50-400"
            )

    def test_narrative_data_driven(self, client, db_session):
        """Narratives should reference actual data (not generic filler)."""
        _seed_rich_data(client)
        from app.services.friday_update import extract_signals, generate_narratives
        signals = extract_signals(db_session)
        narratives = generate_narratives(signals)

        # At least one narrative should mention specific task/initiative names
        all_bodies = " ".join(n["body"] for n in narratives)
        # Check for references to our seeded data
        assert any(
            name in all_bodies
            for name in [
                "Claude CLI", "API", "knowledge",
                "compliance", "leadership", "monitoring",
            ]
        ), "Narratives should reference actual data from the system"

    def test_narratives_with_empty_db(self, client, db_session):
        """Narratives generate gracefully even with no data."""
        from app.services.friday_update import extract_signals, generate_narratives
        signals = extract_signals(db_session)
        narratives = generate_narratives(signals)

        assert len(narratives) == 3
        for n in narratives:
            assert len(n["body"]) > 50


# ---------------------------------------------------------------------------
# Recommended Narrative Tests
# ---------------------------------------------------------------------------

class TestRecommendedNarrative:
    """Tests for the narrative recommendation logic."""

    def test_recommendation_returns_valid_index(self, client, db_session):
        """Recommendation returns a valid index (0, 1, or 2) and a reason."""
        _seed_rich_data(client)
        from app.services.friday_update import (
            extract_signals, generate_narratives, _select_recommended_narrative,
        )
        signals = extract_signals(db_session)
        narratives = generate_narratives(signals)
        idx, reason = _select_recommended_narrative(signals, narratives)

        assert idx in (0, 1, 2)
        assert len(reason) > 20

    def test_high_closures_recommends_execution(self, client, db_session):
        """With many closures, should recommend Execution Progress (index 0)."""
        from app.services.friday_update import (
            generate_narratives, _select_recommended_narrative,
        )
        signals = {
            "commitments_closed": [{"id": str(i), "title": f"t{i}", "closed_at": "2026-03-01"} for i in range(5)],
            "commitments_opened": [],
            "total_open": [],
            "overdue": [],
            "due_soon": [],
            "active_initiatives": [],
            "completed_initiatives": [],
            "stalled_initiatives": [],
            "active_themes": [],
            "recent_comments": [],
            "priorities": [],
        }
        narratives = generate_narratives(signals)
        idx, reason = _select_recommended_narrative(signals, narratives)
        assert idx == 0
        assert "Execution Progress" in reason


# ---------------------------------------------------------------------------
# Week-over-Week Trend Tests
# ---------------------------------------------------------------------------

class TestTrend:
    """Tests for the week-over-week trend comparison."""

    def test_trend_stable_no_previous(self, client, db_session):
        """With no previous update, trend should be stable."""
        from app.services.friday_update import _compute_trend
        trend = _compute_trend(75, None)
        assert trend == "stable"

    def test_trend_up(self, client, db_session):
        """Score increase of 5+ should show 'up' trend."""
        from app.services.friday_update import _compute_trend
        from app.models import WeeklyStrategyUpdate
        prev = WeeklyStrategyUpdate(confidence_score=60)
        trend = _compute_trend(70, prev)
        assert trend == "up"

    def test_trend_down(self, client, db_session):
        """Score decrease of 5+ should show 'down' trend."""
        from app.services.friday_update import _compute_trend
        from app.models import WeeklyStrategyUpdate
        prev = WeeklyStrategyUpdate(confidence_score=80)
        trend = _compute_trend(70, prev)
        assert trend == "down"

    def test_trend_stable_small_change(self, client, db_session):
        """Small score changes (< 5) should show 'stable'."""
        from app.services.friday_update import _compute_trend
        from app.models import WeeklyStrategyUpdate
        prev = WeeklyStrategyUpdate(confidence_score=72)
        trend = _compute_trend(74, prev)
        assert trend == "stable"


# ---------------------------------------------------------------------------
# Email Composition Tests
# ---------------------------------------------------------------------------

class TestEmailComposition:
    """Tests for the email body structure."""

    def test_email_has_all_sections(self, client, db_session):
        """Email body contains all 8 required sections."""
        _seed_rich_data(client)
        resp = client.post("/friday-update", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()

        email_body = data["email_body"]
        assert email_body is not None

        # 1. Greeting
        assert "Brian," in email_body

        # 2-4. Three narrative options
        assert "NARRATIVE OPTION 1" in email_body
        assert "NARRATIVE OPTION 2" in email_body
        assert "NARRATIVE OPTION 3" in email_body

        # Each option has strategic fields
        assert "Strategic Objective:" in email_body
        assert "Why This Framing Works:" in email_body
        assert "Behavior It Drives:" in email_body

        # 5. Recommended
        assert "RECOMMENDED NARRATIVE" in email_body

        # 6. Continuity
        assert "STRATEGIC NARRATIVE CONTINUITY" in email_body

        # 7. Confidence
        assert "STRATEGY CONFIDENCE SIGNAL" in email_body
        assert "Score:" in email_body
        assert "/100" in email_body

        # 8. Forwardable
        assert "FORWARDABLE VERSION" in email_body

    def test_email_no_bullet_lists(self, client, db_session):
        """Email body should not contain bullet lists in narrative sections."""
        _seed_rich_data(client)
        resp = client.post("/friday-update", headers=HEADERS)
        data = resp.json()
        email_body = data["email_body"]

        # Extract narrative sections (between OPTION markers)
        for option_num in range(1, 4):
            start_marker = f"NARRATIVE OPTION {option_num}"
            start_idx = email_body.find(start_marker)
            if option_num < 3:
                end_marker = f"NARRATIVE OPTION {option_num + 1}"
            else:
                end_marker = "RECOMMENDED NARRATIVE"
            end_idx = email_body.find(end_marker)

            if start_idx >= 0 and end_idx >= 0:
                section = email_body[start_idx:end_idx]
                lines = section.split("\n")
                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("---"):
                        assert not stripped.startswith("- "), f"Bullet in option {option_num}: {stripped}"
                        assert not stripped.startswith("* "), f"Bullet in option {option_num}: {stripped}"

    def test_forwardable_version_clean(self, client, db_session):
        """Forwardable version should be a clean standalone message."""
        _seed_rich_data(client)
        resp = client.post("/friday-update", headers=HEADERS)
        data = resp.json()

        forwardable = data["forwardable_body"]
        assert forwardable is not None
        assert "AI Platform" in forwardable
        assert "Weekly Execution Update" in forwardable
        assert "Strategy Confidence:" in forwardable
        assert "/100" in forwardable

        # Should NOT contain the internal framing/option structure
        assert "NARRATIVE OPTION" not in forwardable
        assert "RECOMMENDED NARRATIVE" not in forwardable


# ---------------------------------------------------------------------------
# Endpoint Tests
# ---------------------------------------------------------------------------

class TestFridayUpdateEndpoint:
    """Tests for the /friday-update endpoint."""

    def test_generate_update_empty_db(self, client):
        """Endpoint works with an empty database."""
        resp = client.post("/friday-update", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()

        assert "id" in data
        assert "week_start_date" in data
        assert "confidence_score" in data
        assert data["confidence_score"] is not None
        assert 0 <= data["confidence_score"] <= 100
        assert data["status"] == "DRAFT"  # No Gmail configured

    def test_generate_update_with_data(self, client):
        """Endpoint returns full update with rich data."""
        _seed_rich_data(client)
        resp = client.post("/friday-update", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()

        # Check narrative options
        assert data["narrative_options"] is not None
        assert len(data["narrative_options"]) == 3

        # Check recommended narrative
        assert data["recommended_narrative"] in (0, 1, 2)

        # Check confidence score
        assert 0 <= data["confidence_score"] <= 100
        assert data["confidence_trend"] in ("up", "down", "stable")
        assert len(data["confidence_explanation"]) > 10

        # Check score components
        assert "execution" in data["score_components"]
        assert "momentum" in data["score_components"]
        assert "alignment" in data["score_components"]
        assert "friction" in data["score_components"]

        # Check narrative continuity
        assert data["narrative_continuity"] is not None
        assert len(data["narrative_continuity"]) > 20

        # Check forwardable body
        assert data["forwardable_body"] is not None
        assert "AI Platform" in data["forwardable_body"]

        # Check email body
        assert data["email_body"] is not None
        assert "Brian," in data["email_body"]

    def test_latest_update_404_when_empty(self, client):
        """GET /friday-update/latest returns 404 when no updates exist."""
        resp = client.get("/friday-update/latest", headers=HEADERS)
        assert resp.status_code == 404

    def test_latest_update_after_generate(self, client):
        """GET /friday-update/latest returns the most recent update."""
        # Generate an update first
        client.post("/friday-update", headers=HEADERS)

        resp = client.get("/friday-update/latest", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "confidence_score" in data

    def test_list_updates_empty(self, client):
        """GET /friday-update/list returns empty list when no updates."""
        resp = client.get("/friday-update/list", headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_updates_multiple(self, client):
        """GET /friday-update/list returns multiple updates."""
        client.post("/friday-update", headers=HEADERS)
        _seed_commitment(client, "New task")
        client.post("/friday-update", headers=HEADERS)

        resp = client.get("/friday-update/list", headers=HEADERS)
        assert resp.status_code == 200
        updates = resp.json()
        assert len(updates) == 2

    def test_generate_multiple_updates_has_trend(self, client):
        """Second update should show a trend compared to first."""
        # Generate first update
        resp1 = client.post("/friday-update", headers=HEADERS)
        data1 = resp1.json()
        assert data1["confidence_trend"] == "stable"  # No previous

        # Add some data and generate second
        _seed_rich_data(client)
        resp2 = client.post("/friday-update", headers=HEADERS)
        data2 = resp2.json()
        # Trend should be computed (may be up, down, or stable depending on scores)
        assert data2["confidence_trend"] in ("up", "down", "stable")

    def test_auth_required(self, client):
        """Endpoint requires API key."""
        resp = client.post("/friday-update")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Narrative Continuity Tests
# ---------------------------------------------------------------------------

class TestNarrativeContinuity:
    """Tests for the Strategic Narrative Continuity section."""

    def test_continuity_references_mission(self, client, db_session):
        """Continuity section references the long-term mission."""
        _seed_rich_data(client)
        resp = client.post("/friday-update", headers=HEADERS)
        data = resp.json()

        continuity = data["narrative_continuity"]
        assert "Strategic Narrative" in continuity
        assert "execution" in continuity.lower() or "platform" in continuity.lower()

    def test_continuity_references_themes(self, client, db_session):
        """Continuity section references active strategic themes."""
        _seed_rich_data(client)
        resp = client.post("/friday-update", headers=HEADERS)
        data = resp.json()

        continuity = data["narrative_continuity"]
        # Should reference themes from seeded data
        assert "AI Platform Architecture" in continuity or "Enterprise Integration" in continuity


# ---------------------------------------------------------------------------
# Data Persistence Tests
# ---------------------------------------------------------------------------

class TestPersistence:
    """Tests for data persistence of the WeeklyStrategyUpdate record."""

    def test_update_persisted_to_db(self, client, db_session):
        """Generated update is saved to the database."""
        resp = client.post("/friday-update", headers=HEADERS)
        data = resp.json()

        from app.services.friday_update import get_update
        update = get_update(db_session, update_id=data["id"])
        assert update is not None
        assert update.confidence_score == data["confidence_score"]

    def test_signal_snapshot_persisted(self, client, db_session):
        """Signal snapshot is saved as JSON in the database."""
        _seed_rich_data(client)
        resp = client.post("/friday-update", headers=HEADERS)
        data = resp.json()

        from app.services.friday_update import get_update
        update = get_update(db_session, update_id=data["id"])
        assert update.signal_snapshot is not None

        snapshot = json.loads(update.signal_snapshot)
        assert "total_open" in snapshot
        assert "commitments_closed" in snapshot
        assert "active_initiatives" in snapshot
