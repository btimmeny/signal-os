"""Tests for commitment open, list, close, update, and query."""

from tests.conftest import HEADERS


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["db"] == "connected"


def test_auth_required(client):
    r = client.get("/commitments/open")
    assert r.status_code == 401


def test_open_and_list(client):
    # Open two commitments
    r1 = client.post(
        "/commitments/open",
        json={"title": "Follow up with Alice", "person": "Alice", "urgency": "SOON"},
        headers=HEADERS,
    )
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1["title"] == "Follow up with Alice"
    assert data1["status"] == "OPEN"
    assert data1["person"] == "Alice"
    assert "id" in data1
    assert data1["days_open"] >= 0

    r2 = client.post(
        "/commitments/open",
        json={"title": "Send report to Bob", "person": "Bob"},
        headers=HEADERS,
    )
    assert r2.status_code == 200

    # List open
    r3 = client.get("/commitments/open", headers=HEADERS)
    assert r3.status_code == 200
    items = r3.json()
    assert len(items) == 2
    assert items[0]["title"] == "Follow up with Alice"  # oldest first


def test_close_by_id(client):
    # Open
    r = client.post(
        "/commitments/open",
        json={"title": "Close me", "person": "Charlie"},
        headers=HEADERS,
    )
    cid = r.json()["id"]

    # Close by ID
    r2 = client.post(
        "/commitments/close",
        json={"commitment_id": cid},
        headers=HEADERS,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "CLOSED"
    assert r2.json()["closed_at"] is not None

    # Should not appear in open list
    r3 = client.get("/commitments/open", headers=HEADERS)
    assert len(r3.json()) == 0


def test_close_by_title_exact(client):
    client.post(
        "/commitments/open",
        json={"title": "Unique task"},
        headers=HEADERS,
    )
    r = client.post(
        "/commitments/close",
        json={"title": "Unique task"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "CLOSED"


def test_close_ambiguous_returns_409(client):
    # Two commitments with the same title
    client.post(
        "/commitments/open",
        json={"title": "Duplicate title"},
        headers=HEADERS,
    )
    client.post(
        "/commitments/open",
        json={"title": "Duplicate title"},
        headers=HEADERS,
    )
    r = client.post(
        "/commitments/close",
        json={"title": "Duplicate title"},
        headers=HEADERS,
    )
    assert r.status_code == 409
    body = r.json()
    assert "candidates" in body
    assert len(body["candidates"]) == 2


def test_update(client):
    r = client.post(
        "/commitments/open",
        json={"title": "Update me"},
        headers=HEADERS,
    )
    cid = r.json()["id"]

    r2 = client.post(
        "/commitments/update",
        json={"commitment_id": cid, "urgency": "NOW", "person": "Diana"},
        headers=HEADERS,
    )
    assert r2.status_code == 200
    assert r2.json()["urgency"] == "NOW"
    assert r2.json()["person"] == "Diana"


def test_query_by_person(client):
    client.post(
        "/commitments/open",
        json={"title": "Task A", "person": "Eve"},
        headers=HEADERS,
    )
    client.post(
        "/commitments/open",
        json={"title": "Task B", "person": "Frank"},
        headers=HEADERS,
    )

    r = client.get("/commitments/query?person=Eve", headers=HEADERS)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["person"] == "Eve"


def test_open_with_incident_urgency(client):
    r = client.post(
        "/commitments/open",
        json={"title": "Prod DB is down", "person": "Ops", "urgency": "INCIDENT"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["urgency"] == "INCIDENT"
    assert data["status"] == "OPEN"


def test_update_urgency_to_incident(client):
    r = client.post(
        "/commitments/open",
        json={"title": "Minor bug"},
        headers=HEADERS,
    )
    cid = r.json()["id"]

    r2 = client.post(
        "/commitments/update",
        json={"commitment_id": cid, "urgency": "INCIDENT"},
        headers=HEADERS,
    )
    assert r2.status_code == 200
    assert r2.json()["urgency"] == "INCIDENT"


def test_query_by_incident_urgency(client):
    client.post(
        "/commitments/open",
        json={"title": "Prod outage", "urgency": "INCIDENT"},
        headers=HEADERS,
    )
    client.post(
        "/commitments/open",
        json={"title": "Normal task", "urgency": "SOON"},
        headers=HEADERS,
    )

    r = client.get("/commitments/query?urgency=INCIDENT", headers=HEADERS)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["urgency"] == "INCIDENT"
    assert items[0]["title"] == "Prod outage"


def test_open_with_admin_urgency(client):
    r = client.post(
        "/commitments/open",
        json={"title": "Update docs", "person": "Self", "urgency": "ADMIN"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["urgency"] == "ADMIN"
    assert data["status"] == "OPEN"


def test_update_urgency_to_admin(client):
    r = client.post(
        "/commitments/open",
        json={"title": "Cleanup logs"},
        headers=HEADERS,
    )
    cid = r.json()["id"]

    r2 = client.post(
        "/commitments/update",
        json={"commitment_id": cid, "urgency": "ADMIN"},
        headers=HEADERS,
    )
    assert r2.status_code == 200
    assert r2.json()["urgency"] == "ADMIN"


def test_query_by_admin_urgency(client):
    client.post(
        "/commitments/open",
        json={"title": "Rotate API keys", "urgency": "ADMIN"},
        headers=HEADERS,
    )
    client.post(
        "/commitments/open",
        json={"title": "Ship feature", "urgency": "NOW"},
        headers=HEADERS,
    )

    r = client.get("/commitments/query?urgency=ADMIN", headers=HEADERS)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["urgency"] == "ADMIN"
    assert items[0]["title"] == "Rotate API keys"


def test_open_with_priority_order(client):
    r = client.post(
        "/commitments/open",
        json={"title": "Top priority task", "person": "Alice", "priority_order": 1},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["priority_order"] == 1
    assert data["status"] == "OPEN"


def test_set_priority(client):
    r = client.post(
        "/commitments/open",
        json={"title": "Task to prioritize"},
        headers=HEADERS,
    )
    cid = r.json()["id"]
    assert r.json()["priority_order"] is None

    r2 = client.post(
        "/commitments/set_priority",
        json={"commitment_id": cid, "priority_order": 1},
        headers=HEADERS,
    )
    assert r2.status_code == 200
    assert r2.json()["priority_order"] == 1


def test_priority_reordering(client):
    # Create three commitments with priorities 1, 2, 3
    ids = []
    for i, title in enumerate(["First", "Second", "Third"], start=1):
        r = client.post(
            "/commitments/open",
            json={"title": title, "priority_order": i},
            headers=HEADERS,
        )
        assert r.status_code == 200
        ids.append(r.json()["id"])

    # Insert a new commitment at position 2 — should push Second->3, Third->4
    r = client.post(
        "/commitments/open",
        json={"title": "Inserted at 2", "priority_order": 2},
        headers=HEADERS,
    )
    assert r.status_code == 200
    new_id = r.json()["id"]

    # Check the priority list
    r2 = client.get("/commitments/priorities", headers=HEADERS)
    assert r2.status_code == 200
    items = r2.json()
    assert len(items) == 4
    assert items[0]["title"] == "First"
    assert items[0]["priority_order"] == 1
    assert items[1]["title"] == "Inserted at 2"
    assert items[1]["priority_order"] == 2
    assert items[2]["title"] == "Second"
    assert items[2]["priority_order"] == 3
    assert items[3]["title"] == "Third"
    assert items[3]["priority_order"] == 4


def test_list_priorities(client):
    # Create commitments — some with priority, some without
    client.post(
        "/commitments/open",
        json={"title": "No priority"},
        headers=HEADERS,
    )
    # Create in ascending order so no reordering shifts occur
    client.post(
        "/commitments/open",
        json={"title": "Priority 1", "priority_order": 1},
        headers=HEADERS,
    )
    client.post(
        "/commitments/open",
        json={"title": "Priority 2", "priority_order": 2},
        headers=HEADERS,
    )

    r = client.get("/commitments/priorities", headers=HEADERS)
    assert r.status_code == 200
    items = r.json()
    # Only commitments with priority_order should appear
    assert len(items) == 2
    assert items[0]["title"] == "Priority 1"
    assert items[0]["priority_order"] == 1
    assert items[1]["title"] == "Priority 2"
    assert items[1]["priority_order"] == 2


def test_update_priority_order(client):
    r = client.post(
        "/commitments/open",
        json={"title": "Task with priority", "priority_order": 1},
        headers=HEADERS,
    )
    cid = r.json()["id"]

    r2 = client.post(
        "/commitments/update",
        json={"commitment_id": cid, "priority_order": 5},
        headers=HEADERS,
    )
    assert r2.status_code == 200
    assert r2.json()["priority_order"] == 5


def test_query_by_text(client):
    client.post(
        "/commitments/open",
        json={"title": "Review PR #42", "description": "Needs security review"},
        headers=HEADERS,
    )
    client.post(
        "/commitments/open",
        json={"title": "Buy groceries"},
        headers=HEADERS,
    )

    r = client.get("/commitments/query?text=security", headers=HEADERS)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert "PR #42" in items[0]["title"]
