"""Tests for reminder create, due listing, and dispatch."""

from datetime import datetime, timedelta, timezone

from tests.conftest import HEADERS


def test_create_reminder_and_list_due(client):
    # Open a commitment first
    r = client.post(
        "/commitments/open",
        json={"title": "Remind me about this"},
        headers=HEADERS,
    )
    cid = r.json()["id"]

    # Create a reminder in the past (so it's immediately due)
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    r2 = client.post(
        "/reminders/create",
        json={
            "commitment_id": cid,
            "remind_at": past,
            "message": "Don't forget!",
            "delivery_target": "+15551234567",
        },
        headers=HEADERS,
    )
    assert r2.status_code == 200
    reminder = r2.json()
    assert reminder["commitment_id"] == cid
    assert reminder["sent_at"] is None

    # List due reminders
    r3 = client.get("/reminders/due", headers=HEADERS)
    assert r3.status_code == 200
    due = r3.json()
    assert len(due) == 1
    assert due[0]["id"] == reminder["id"]


def test_dispatch_due_reminders(client):
    # Open commitment
    r = client.post(
        "/commitments/open",
        json={"title": "Dispatch test"},
        headers=HEADERS,
    )
    cid = r.json()["id"]

    # Create past-due reminder
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    client.post(
        "/reminders/create",
        json={"commitment_id": cid, "remind_at": past},
        headers=HEADERS,
    )

    # Dispatch
    r2 = client.post("/reminders/dispatch_due", headers=HEADERS)
    assert r2.status_code == 200
    dispatched = r2.json()
    assert len(dispatched) == 1
    assert dispatched[0]["sent_at"] is not None

    # Due list should now be empty
    r3 = client.get("/reminders/due", headers=HEADERS)
    assert len(r3.json()) == 0


def test_future_reminder_not_due(client):
    r = client.post(
        "/commitments/open",
        json={"title": "Future reminder"},
        headers=HEADERS,
    )
    cid = r.json()["id"]

    future = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    client.post(
        "/reminders/create",
        json={"commitment_id": cid, "remind_at": future},
        headers=HEADERS,
    )

    r2 = client.get("/reminders/due", headers=HEADERS)
    assert len(r2.json()) == 0
