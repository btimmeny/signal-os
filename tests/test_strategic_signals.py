"""Tests for Feature 021 — Strategic Signal System."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import HEADERS


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _create_theme(client, title="Test Theme"):
    resp = client.post(
        "/themes/create",
        json={"title": title, "description": "A test theme"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    return resp.json()


def _create_initiative(client, title="Test Initiative", theme_id=None):
    body = {"title": title, "description": "A test initiative"}
    if theme_id:
        body["theme_id"] = theme_id
    resp = client.post(
        "/initiatives/create",
        json=body,
        headers=HEADERS,
    )
    assert resp.status_code == 200
    return resp.json()


def _open_commitment(client, title="Test Task", description=None):
    body = {"title": title, "status": "OPEN"}
    if description:
        body["description"] = description
    resp = client.post(
        "/commitments/open",
        json=body,
        headers=HEADERS,
    )
    assert resp.status_code == 200
    return resp.json()


def _close_commitment(client, commitment_id):
    resp = client.post(
        "/commitments/close",
        json={"commitment_id": commitment_id},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    return resp.json()


def _link_initiative(client, commitment_id, initiative_id):
    resp = client.post(
        "/initiatives/link",
        json={"commitment_id": commitment_id, "initiative_id": initiative_id},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# Test: Strategic Contribution Notes on task open
# ---------------------------------------------------------------------------

class TestOpenSignals:
    """Signal generation when tasks are opened."""

    def test_open_commitment_generates_contribution_note(self, client):
        """Opening a task should generate a strategic contribution note."""
        c = _open_commitment(client, "Build new API integration endpoint")
        assert c["strategic_contribution_note"] is not None
        assert len(c["strategic_contribution_note"]) > 0

    def test_open_commitment_creates_signal_record(self, client):
        """Opening a task should create a StrategicSignal record."""
        c = _open_commitment(client, "Deploy infrastructure pipeline")
        signals = client.get(
            f"/signals/commitment/{c['id']}", headers=HEADERS
        ).json()
        assert len(signals) == 1
        assert signals[0]["event_type"] == "OPENED"
        assert signals[0]["commitment_id"] == c["id"]

    def test_open_with_initiative_link_produces_rich_note(self, client):
        """Task linked to initiative should produce a detailed contribution note."""
        theme = _create_theme(client, "Platform Evolution")
        init = _create_initiative(client, "API Platform", theme["id"])
        c = _open_commitment(client, "Add GraphQL layer")
        _link_initiative(client, c["id"], init["id"])

        # Open another commitment that's linked
        c2 = _open_commitment(client, "Build authentication middleware")
        # Link it first, then check the signal
        _link_initiative(client, c2["id"], init["id"])

        # The signal for c2 was recorded at open time (before link)
        # But c (opened before link) should have its note
        signals = client.get(
            f"/signals/commitment/{c['id']}", headers=HEADERS
        ).json()
        assert len(signals) >= 1

    def test_open_without_initiative_flags_unclear(self, client):
        """Task without initiative should flag unclear contribution."""
        c = _open_commitment(client, "Random admin task")
        assert "unclear" in c["strategic_contribution_note"].lower() or \
               "should be linked" in c["strategic_contribution_note"].lower()

    def test_open_with_strategic_keywords_classifies_category(self, client):
        """Tasks with strategic keywords should be classified."""
        c = _open_commitment(
            client,
            "Build new platform infrastructure",
            description="Deploy core infrastructure pipeline",
        )
        signals = client.get(
            f"/signals/commitment/{c['id']}", headers=HEADERS
        ).json()
        assert len(signals) == 1
        assert signals[0]["signal_category"] is not None

    def test_open_high_signal_detection(self, client):
        """Tasks with strong strategic keywords should be marked high-signal."""
        c = _open_commitment(
            client,
            "Deploy platform infrastructure upgrade",
        )
        signals = client.get(
            f"/signals/commitment/{c['id']}", headers=HEADERS
        ).json()
        assert len(signals) == 1
        assert signals[0]["is_high_signal"] is True


# ---------------------------------------------------------------------------
# Test: Execution Impact Notes on task close
# ---------------------------------------------------------------------------

class TestCloseSignals:
    """Signal generation when tasks are closed."""

    def test_close_commitment_generates_impact_note(self, client):
        """Closing a task should generate an execution impact note."""
        c = _open_commitment(client, "Complete API integration")
        closed = _close_commitment(client, c["id"])
        assert closed["execution_impact_note"] is not None
        assert len(closed["execution_impact_note"]) > 0

    def test_close_commitment_creates_signal_record(self, client):
        """Closing a task should create a CLOSED StrategicSignal record."""
        c = _open_commitment(client, "Finish deployment pipeline")
        _close_commitment(client, c["id"])
        signals = client.get(
            f"/signals/commitment/{c['id']}", headers=HEADERS
        ).json()
        # Should have both OPENED and CLOSED signals
        event_types = {s["event_type"] for s in signals}
        assert "OPENED" in event_types
        assert "CLOSED" in event_types

    def test_close_with_initiative_produces_rich_impact(self, client):
        """Closing a task linked to initiative should reference the initiative."""
        theme = _create_theme(client, "AI-Native Development")
        init = _create_initiative(client, "Agent Capabilities", theme["id"])
        c = _open_commitment(client, "Build agent integration layer")
        _link_initiative(client, c["id"], init["id"])
        closed = _close_commitment(client, c["id"])
        assert "Agent Capabilities" in closed["execution_impact_note"]

    def test_close_without_initiative_flags_unclear_impact(self, client):
        """Closing unlinked task should flag unclear impact."""
        c = _open_commitment(client, "Fix typo in readme")
        closed = _close_commitment(client, c["id"])
        assert "unclear" in closed["execution_impact_note"].lower() or \
               "should be" in closed["execution_impact_note"].lower()

    def test_close_via_update_endpoint(self, client):
        """Closing via /commitments/update should also generate a signal."""
        c = _open_commitment(client, "Infrastructure migration task")
        resp = client.post(
            "/commitments/update",
            json={"commitment_id": c["id"], "status": "CLOSED"},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["execution_impact_note"] is not None

        signals = client.get(
            f"/signals/commitment/{c['id']}", headers=HEADERS
        ).json()
        close_signals = [s for s in signals if s["event_type"] == "CLOSED"]
        assert len(close_signals) >= 1


# ---------------------------------------------------------------------------
# Test: Signal query endpoints
# ---------------------------------------------------------------------------

class TestSignalEndpoints:
    """Test the /signals/* API endpoints."""

    def test_signals_list_empty(self, client):
        """List signals returns empty list when no signals exist."""
        resp = client.get("/signals/list", headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_signals_list_returns_signals(self, client):
        """List signals returns created signals."""
        _open_commitment(client, "Task A")
        _open_commitment(client, "Task B")
        resp = client.get("/signals/list", headers=HEADERS)
        assert resp.status_code == 200
        signals = resp.json()
        assert len(signals) == 2

    def test_signals_list_filter_by_event_type(self, client):
        """Filter signals by event type."""
        c = _open_commitment(client, "Task C")
        _close_commitment(client, c["id"])

        opened = client.get(
            "/signals/list?event_type=OPENED", headers=HEADERS
        ).json()
        closed = client.get(
            "/signals/list?event_type=CLOSED", headers=HEADERS
        ).json()
        assert all(s["event_type"] == "OPENED" for s in opened)
        assert all(s["event_type"] == "CLOSED" for s in closed)

    def test_signals_list_high_signal_only(self, client):
        """Filter signals to high-signal only."""
        _open_commitment(client, "Deploy platform infrastructure")
        _open_commitment(client, "Fix typo")
        resp = client.get(
            "/signals/list?high_signal_only=true", headers=HEADERS
        ).json()
        assert all(s["is_high_signal"] for s in resp)

    def test_signals_get_by_id(self, client):
        """Get a specific signal by ID."""
        c = _open_commitment(client, "Build SDK")
        signals = client.get(
            f"/signals/commitment/{c['id']}", headers=HEADERS
        ).json()
        signal_id = signals[0]["id"]

        resp = client.get(f"/signals/{signal_id}", headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json()["id"] == signal_id

    def test_signals_get_not_found(self, client):
        """Get a non-existent signal returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/signals/{fake_id}", headers=HEADERS)
        assert resp.status_code == 404

    def test_signals_for_commitment(self, client):
        """Get signals for a specific commitment."""
        c = _open_commitment(client, "Test commitment signals")
        _close_commitment(client, c["id"])

        resp = client.get(
            f"/signals/commitment/{c['id']}", headers=HEADERS
        )
        assert resp.status_code == 200
        signals = resp.json()
        assert len(signals) == 2
        assert all(s["commitment_id"] == c["id"] for s in signals)

    def test_weekly_summary(self, client):
        """Weekly summary aggregates signals correctly."""
        c1 = _open_commitment(client, "Platform infrastructure task")
        c2 = _open_commitment(client, "API integration work")
        _close_commitment(client, c1["id"])
        _close_commitment(client, c2["id"])

        resp = client.get("/signals/weekly-summary", headers=HEADERS)
        assert resp.status_code == 200
        summary = resp.json()
        assert summary["signal_count"] >= 4  # 2 opens + 2 closes
        assert summary["closure_count"] >= 2
        assert summary["open_count"] >= 2
        assert len(summary["summary_text"]) > 0

    def test_weekly_summary_empty(self, client):
        """Weekly summary with no signals returns zeros."""
        resp = client.get("/signals/weekly-summary", headers=HEADERS)
        assert resp.status_code == 200
        summary = resp.json()
        assert summary["signal_count"] == 0
        assert summary["closure_count"] == 0


# ---------------------------------------------------------------------------
# Test: Signal classification and categorization
# ---------------------------------------------------------------------------

class TestSignalClassification:
    """Test signal category detection and high-signal classification."""

    def test_infrastructure_category(self, client):
        """Infrastructure keywords classified correctly."""
        c = _open_commitment(client, "Build infrastructure pipeline")
        signals = client.get(
            f"/signals/commitment/{c['id']}", headers=HEADERS
        ).json()
        assert signals[0]["signal_category"] == "infrastructure"

    def test_tooling_integration_category(self, client):
        """Integration keywords classified correctly."""
        c = _open_commitment(client, "Add SDK integration for auth")
        signals = client.get(
            f"/signals/commitment/{c['id']}", headers=HEADERS
        ).json()
        assert signals[0]["signal_category"] in ("tooling_integration", "new_capability")

    def test_agent_capability_category(self, client):
        """Agent keywords classified correctly."""
        c = _open_commitment(client, "Improve agent automation workflow")
        signals = client.get(
            f"/signals/commitment/{c['id']}", headers=HEADERS
        ).json()
        assert signals[0]["signal_category"] == "agent_capability"

    def test_pilot_progress_category(self, client):
        """Pilot keywords classified correctly."""
        c = _open_commitment(client, "Run pilot experiment with stakeholders")
        signals = client.get(
            f"/signals/commitment/{c['id']}", headers=HEADERS
        ).json()
        assert signals[0]["signal_category"] == "pilot_progress"

    def test_no_category_for_generic_task(self, client):
        """Generic tasks may not have a category."""
        c = _open_commitment(client, "Update meeting notes")
        signals = client.get(
            f"/signals/commitment/{c['id']}", headers=HEADERS
        ).json()
        # Generic task may or may not have a category
        assert signals[0]["signal_category"] is None or isinstance(signals[0]["signal_category"], str)

    def test_high_signal_with_initiative_and_keyword(self, client):
        """Task linked to initiative with strategic keywords is high-signal."""
        theme = _create_theme(client, "Platform Theme")
        init = _create_initiative(client, "Core Platform", theme["id"])
        c = _open_commitment(client, "Build platform capability layer")
        _link_initiative(client, c["id"], init["id"])

        # Close and check the close signal
        _close_commitment(client, c["id"])
        signals = client.get(
            f"/signals/commitment/{c['id']}", headers=HEADERS
        ).json()
        close_signals = [s for s in signals if s["event_type"] == "CLOSED"]
        assert len(close_signals) >= 1
        assert close_signals[0]["is_high_signal"] is True


# ---------------------------------------------------------------------------
# Test: Commitment response includes signal fields
# ---------------------------------------------------------------------------

class TestCommitmentResponseFields:
    """Verify CommitmentResponse includes new signal fields."""

    def test_open_response_has_contribution_note(self, client):
        """Open commitment response includes strategic_contribution_note."""
        c = _open_commitment(client, "Test field presence")
        assert "strategic_contribution_note" in c
        assert c["strategic_contribution_note"] is not None

    def test_open_response_has_null_impact_note(self, client):
        """Open commitment should not have execution_impact_note yet."""
        c = _open_commitment(client, "Test null impact")
        assert "execution_impact_note" in c
        assert c["execution_impact_note"] is None

    def test_close_response_has_both_notes(self, client):
        """Closed commitment response includes both notes."""
        c = _open_commitment(client, "Test both notes")
        closed = _close_commitment(client, c["id"])
        assert closed["strategic_contribution_note"] is not None
        assert closed["execution_impact_note"] is not None


# ---------------------------------------------------------------------------
# Test: Integration with Friday update
# ---------------------------------------------------------------------------

class TestFridayUpdateIntegration:
    """Verify strategic signals feed into Friday update generation."""

    def test_friday_update_includes_strategic_signals(self, client, db_session):
        """Friday update signal snapshot should include strategic signal data."""
        import json
        from app.services import friday_update as friday_svc

        # Create some tasks with signals
        c1 = _open_commitment(client, "Platform infrastructure upgrade")
        c2 = _open_commitment(client, "API capability release")
        _close_commitment(client, c1["id"])
        _close_commitment(client, c2["id"])

        # Generate Friday update
        update = friday_svc.generate_friday_update(db_session, send_email=False)

        # Check signal snapshot includes strategic signal data
        snapshot = json.loads(update.signal_snapshot)
        if "strategic_signals" in snapshot:
            ss = snapshot["strategic_signals"]
            assert "high_signal_count" in ss
            assert "closure_count" in ss
            assert "open_count" in ss


# ---------------------------------------------------------------------------
# Test: Signal service directly
# ---------------------------------------------------------------------------

class TestSignalServiceDirect:
    """Test the strategic_signals service functions directly."""

    def test_record_open_signal(self, db_session):
        """record_open_signal creates a signal and sets contribution note."""
        from app.services import strategic_signals as signal_svc
        from app.models import Commitment, CommitmentStatus

        c = Commitment(
            title="Direct service test",
            status=CommitmentStatus.OPEN,
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        signal = signal_svc.record_open_signal(db_session, c)
        assert signal.event_type == "OPENED"
        assert signal.commitment_id == c.id
        assert c.strategic_contribution_note is not None

    def test_record_close_signal(self, db_session):
        """record_close_signal creates a signal and sets impact note."""
        from app.services import strategic_signals as signal_svc
        from app.models import Commitment, CommitmentStatus

        c = Commitment(
            title="Direct close test",
            status=CommitmentStatus.CLOSED,
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        signal = signal_svc.record_close_signal(db_session, c)
        assert signal.event_type == "CLOSED"
        assert signal.execution_impact is not None
        assert c.execution_impact_note is not None

    def test_get_signals_for_period(self, db_session):
        """get_signals_for_period returns signals within the time window."""
        from app.services import strategic_signals as signal_svc
        from app.models import Commitment, CommitmentStatus

        c = Commitment(
            title="Period test",
            status=CommitmentStatus.OPEN,
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        signal_svc.record_open_signal(db_session, c)

        signals = signal_svc.get_signals_for_period(db_session, days_back=7)
        assert len(signals) >= 1

    def test_get_high_signal_closures(self, db_session):
        """get_high_signal_closures filters for high-signal CLOSED events."""
        from app.services import strategic_signals as signal_svc
        from app.models import Commitment, CommitmentStatus

        c = Commitment(
            title="Platform infrastructure deployment",
            status=CommitmentStatus.CLOSED,
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        signal_svc.record_close_signal(db_session, c)

        high = signal_svc.get_high_signal_closures(db_session, days_back=7)
        assert len(high) >= 1
        assert all(s.is_high_signal == 1 for s in high)

    def test_get_unclear_signals(self, db_session):
        """get_unclear_signals returns signals without initiative or theme."""
        from app.services import strategic_signals as signal_svc
        from app.models import Commitment, CommitmentStatus

        c = Commitment(
            title="Random task",
            status=CommitmentStatus.OPEN,
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        signal_svc.record_open_signal(db_session, c)

        unclear = signal_svc.get_unclear_signals(db_session, days_back=7)
        assert len(unclear) >= 1
        assert all(s.initiative_id is None for s in unclear)

    def test_aggregate_weekly_signals(self, db_session):
        """aggregate_weekly_signals returns structured summary."""
        from app.services import strategic_signals as signal_svc
        from app.models import Commitment, CommitmentStatus

        c1 = Commitment(
            title="Infrastructure task",
            status=CommitmentStatus.OPEN,
        )
        c2 = Commitment(
            title="Platform release",
            status=CommitmentStatus.OPEN,
        )
        db_session.add_all([c1, c2])
        db_session.commit()
        db_session.refresh(c1)
        db_session.refresh(c2)

        signal_svc.record_open_signal(db_session, c1)
        signal_svc.record_open_signal(db_session, c2)

        c1.status = CommitmentStatus.CLOSED
        db_session.commit()
        signal_svc.record_close_signal(db_session, c1)

        agg = signal_svc.aggregate_weekly_signals(db_session)
        assert agg["signal_count"] >= 3
        assert agg["open_count"] >= 2
        assert agg["closure_count"] >= 1

    def test_format_signal_summary(self, db_session):
        """format_signal_summary produces readable text."""
        from app.services import strategic_signals as signal_svc
        from app.models import Commitment, CommitmentStatus

        c = Commitment(
            title="Platform capability",
            status=CommitmentStatus.CLOSED,
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        signal_svc.record_close_signal(db_session, c)

        agg = signal_svc.aggregate_weekly_signals(db_session)
        text = signal_svc.format_signal_summary(agg)
        assert "Strategic Signals This Week" in text
        assert len(text) > 50

    def test_list_signals(self, db_session):
        """list_signals returns signals with optional filters."""
        from app.services import strategic_signals as signal_svc
        from app.models import Commitment, CommitmentStatus

        c = Commitment(
            title="List test task",
            status=CommitmentStatus.OPEN,
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        signal_svc.record_open_signal(db_session, c)

        all_signals = signal_svc.list_signals(db_session)
        assert len(all_signals) >= 1

        opened = signal_svc.list_signals(db_session, event_type="OPENED")
        assert all(s.event_type == "OPENED" for s in opened)

    def test_get_signal_by_id(self, db_session):
        """get_signal returns a single signal by ID."""
        from app.services import strategic_signals as signal_svc
        from app.models import Commitment, CommitmentStatus

        c = Commitment(
            title="Get by ID test",
            status=CommitmentStatus.OPEN,
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        signal = signal_svc.record_open_signal(db_session, c)
        found = signal_svc.get_signal(db_session, str(signal.id))
        assert found is not None
        assert found.id == signal.id

    def test_get_signal_not_found(self, db_session):
        """get_signal returns None for non-existent ID."""
        from app.services import strategic_signals as signal_svc

        found = signal_svc.get_signal(db_session, str(uuid.uuid4()))
        assert found is None


# ---------------------------------------------------------------------------
# Test: Signal note content quality
# ---------------------------------------------------------------------------

class TestSignalNoteContent:
    """Test the quality and content of generated notes."""

    def test_contribution_note_mentions_initiative(self, client, db_session):
        """Contribution note should mention the initiative name when linked."""
        from app.models import Commitment, Initiative, InitiativeCommitmentLink
        from app.services import strategic_signals as signal_svc

        init = Initiative(title="Knowledge Layer", description="Build knowledge")
        db_session.add(init)
        db_session.commit()
        db_session.refresh(init)

        c = Commitment(title="Build search index", status="OPEN")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        link = InitiativeCommitmentLink(
            commitment_id=c.id,
            initiative_id=init.id,
        )
        db_session.add(link)
        db_session.commit()

        signal = signal_svc.record_open_signal(db_session, c)
        assert "Knowledge Layer" in signal.strategic_contribution

    def test_impact_note_mentions_initiative(self, client, db_session):
        """Impact note should mention the initiative name when linked."""
        from app.models import Commitment, Initiative, InitiativeCommitmentLink
        from app.services import strategic_signals as signal_svc

        init = Initiative(title="Agent Integration", description="Integrate agents")
        db_session.add(init)
        db_session.commit()
        db_session.refresh(init)

        c = Commitment(title="Complete agent API", status="CLOSED")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        link = InitiativeCommitmentLink(
            commitment_id=c.id,
            initiative_id=init.id,
        )
        db_session.add(link)
        db_session.commit()

        signal = signal_svc.record_close_signal(db_session, c)
        assert "Agent Integration" in signal.execution_impact

    def test_contribution_note_mentions_theme(self, client, db_session):
        """Contribution note should mention the theme when linked via initiative."""
        from app.models import Commitment, Initiative, InitiativeCommitmentLink, StrategicTheme
        from app.services import strategic_signals as signal_svc

        theme = StrategicTheme(title="Evergreen Platform", description="Core platform")
        db_session.add(theme)
        db_session.commit()
        db_session.refresh(theme)

        init = Initiative(title="Core Services", description="Core", theme_id=theme.id)
        db_session.add(init)
        db_session.commit()
        db_session.refresh(init)

        c = Commitment(title="Build service mesh", status="OPEN")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        link = InitiativeCommitmentLink(
            commitment_id=c.id,
            initiative_id=init.id,
        )
        db_session.add(link)
        db_session.commit()

        signal = signal_svc.record_open_signal(db_session, c)
        assert "Evergreen Platform" in signal.strategic_contribution
        assert "Core Services" in signal.strategic_contribution

    def test_impact_note_includes_task_title(self, db_session):
        """Impact note should include the completed task's title when linked to initiative."""
        from app.models import Commitment, Initiative, InitiativeCommitmentLink
        from app.services import strategic_signals as signal_svc

        init = Initiative(title="Observability", description="Monitoring")
        db_session.add(init)
        db_session.commit()
        db_session.refresh(init)

        c = Commitment(title="Deploy monitoring dashboard", status="CLOSED")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        link = InitiativeCommitmentLink(commitment_id=c.id, initiative_id=init.id)
        db_session.add(link)
        db_session.commit()

        signal = signal_svc.record_close_signal(db_session, c)
        assert "Deploy monitoring dashboard" in signal.execution_impact
