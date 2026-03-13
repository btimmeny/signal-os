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
    # Create two items so we can move one to position 2
    r = client.post(
        "/commitments/open",
        json={"title": "Task A", "priority_order": 1},
        headers=HEADERS,
    )
    cid_a = r.json()["id"]

    client.post(
        "/commitments/open",
        json={"title": "Task B", "priority_order": 2},
        headers=HEADERS,
    )

    # Move Task A to position 2 via update endpoint
    r2 = client.post(
        "/commitments/update",
        json={"commitment_id": cid_a, "priority_order": 2},
        headers=HEADERS,
    )
    assert r2.status_code == 200
    assert r2.json()["priority_order"] == 2

    # Verify order: B=1, A=2
    r3 = client.get("/commitments/priorities", headers=HEADERS)
    items = r3.json()
    assert items[0]["title"] == "Task B"
    assert items[0]["priority_order"] == 1
    assert items[1]["title"] == "Task A"
    assert items[1]["priority_order"] == 2


def test_set_priority_move_down(client):
    """Moving an item from position 1 to position 3 should shift others up."""
    ids = []
    for i, title in enumerate(["A", "B", "C"], start=1):
        r = client.post(
            "/commitments/open",
            json={"title": title, "priority_order": i},
            headers=HEADERS,
        )
        assert r.status_code == 200
        ids.append(r.json()["id"])

    # Move A from position 1 to position 3
    r = client.post(
        "/commitments/set_priority",
        json={"commitment_id": ids[0], "priority_order": 3},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["priority_order"] == 3

    # Verify: B=1, C=2, A=3
    r2 = client.get("/commitments/priorities", headers=HEADERS)
    items = r2.json()
    assert len(items) == 3
    assert items[0]["title"] == "B"
    assert items[0]["priority_order"] == 1
    assert items[1]["title"] == "C"
    assert items[1]["priority_order"] == 2
    assert items[2]["title"] == "A"
    assert items[2]["priority_order"] == 3


def test_set_priority_move_up(client):
    """Moving an item from position 3 to position 1 should shift others down."""
    ids = []
    for i, title in enumerate(["A", "B", "C"], start=1):
        r = client.post(
            "/commitments/open",
            json={"title": title, "priority_order": i},
            headers=HEADERS,
        )
        assert r.status_code == 200
        ids.append(r.json()["id"])

    # Move C from position 3 to position 1
    r = client.post(
        "/commitments/set_priority",
        json={"commitment_id": ids[2], "priority_order": 1},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["priority_order"] == 1

    # Verify: C=1, A=2, B=3
    r2 = client.get("/commitments/priorities", headers=HEADERS)
    items = r2.json()
    assert len(items) == 3
    assert items[0]["title"] == "C"
    assert items[0]["priority_order"] == 1
    assert items[1]["title"] == "A"
    assert items[1]["priority_order"] == 2
    assert items[2]["title"] == "B"
    assert items[2]["priority_order"] == 3


def test_priority_order_rejects_zero(client):
    """priority_order=0 should be rejected by validation."""
    r = client.post(
        "/commitments/open",
        json={"title": "Bad priority", "priority_order": 0},
        headers=HEADERS,
    )
    assert r.status_code == 422


def test_priority_order_rejects_negative(client):
    """priority_order=-1 should be rejected by validation."""
    r = client.post(
        "/commitments/open",
        json={"title": "Negative priority", "priority_order": -1},
        headers=HEADERS,
    )
    assert r.status_code == 422


def test_update_priority_order_rejects_zero(client):
    """priority_order=0 via update should be rejected by validation."""
    r = client.post(
        "/commitments/open",
        json={"title": "Some task"},
        headers=HEADERS,
    )
    cid = r.json()["id"]

    r2 = client.post(
        "/commitments/update",
        json={"commitment_id": cid, "priority_order": 0},
        headers=HEADERS,
    )
    assert r2.status_code == 422


def test_add_comment(client):
    """Add a comment to a commitment and verify it's returned."""
    r = client.post(
        "/commitments/open",
        json={"title": "Task with comments", "person": "Alice"},
        headers=HEADERS,
    )
    cid = r.json()["id"]

    r2 = client.post(
        "/commitments/comment",
        json={"commitment_id": cid, "body": "Had a meeting about this", "author": "Alice"},
        headers=HEADERS,
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["body"] == "Had a meeting about this"
    assert data["author"] == "Alice"
    assert data["commitment_id"] == cid
    assert "id" in data
    assert "created_at" in data


def test_list_comments(client):
    """List comments for a commitment, ordered oldest first."""
    r = client.post(
        "/commitments/open",
        json={"title": "Task for comment listing"},
        headers=HEADERS,
    )
    cid = r.json()["id"]

    # Add two comments
    client.post(
        "/commitments/comment",
        json={"commitment_id": cid, "body": "First update"},
        headers=HEADERS,
    )
    client.post(
        "/commitments/comment",
        json={"commitment_id": cid, "body": "Second update", "author": "Bob"},
        headers=HEADERS,
    )

    r2 = client.get(f"/commitments/comments?commitment_id={cid}", headers=HEADERS)
    assert r2.status_code == 200
    items = r2.json()
    assert len(items) == 2
    assert items[0]["body"] == "First update"
    assert items[0]["author"] is None
    assert items[1]["body"] == "Second update"
    assert items[1]["author"] == "Bob"


def test_comment_on_nonexistent_commitment(client):
    """Adding a comment to a non-existent commitment returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.post(
        "/commitments/comment",
        json={"commitment_id": fake_id, "body": "This should fail"},
        headers=HEADERS,
    )
    assert r.status_code == 404


def test_list_comments_nonexistent_commitment(client):
    """Listing comments for a non-existent commitment returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.get(f"/commitments/comments?commitment_id={fake_id}", headers=HEADERS)
    assert r.status_code == 404


def test_comment_empty_body_rejected(client):
    """A comment with an empty body should be rejected."""
    r = client.post(
        "/commitments/open",
        json={"title": "Task for empty comment test"},
        headers=HEADERS,
    )
    cid = r.json()["id"]

    r2 = client.post(
        "/commitments/comment",
        json={"commitment_id": cid, "body": ""},
        headers=HEADERS,
    )
    assert r2.status_code == 422


def test_comments_empty_for_new_commitment(client):
    """A new commitment should have no comments."""
    r = client.post(
        "/commitments/open",
        json={"title": "Fresh task"},
        headers=HEADERS,
    )
    cid = r.json()["id"]

    r2 = client.get(f"/commitments/comments?commitment_id={cid}", headers=HEADERS)
    assert r2.status_code == 200
    assert r2.json() == []


def test_comments_persist_after_close(client):
    """Comments should persist after closing the parent commitment."""
    r = client.post(
        "/commitments/open",
        json={"title": "Task to close with comments"},
        headers=HEADERS,
    )
    cid = r.json()["id"]

    # Add a comment
    client.post(
        "/commitments/comment",
        json={"commitment_id": cid, "body": "Some progress note"},
        headers=HEADERS,
    )

    # Verify comment exists
    r2 = client.get(f"/commitments/comments?commitment_id={cid}", headers=HEADERS)
    assert len(r2.json()) == 1

    # Close the commitment - comments should still be accessible
    client.post(
        "/commitments/close",
        json={"commitment_id": cid},
        headers=HEADERS,
    )

    # Comments should still be there (closing doesn't delete)
    r3 = client.get(f"/commitments/comments?commitment_id={cid}", headers=HEADERS)
    assert r3.status_code == 200
    assert len(r3.json()) == 1


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


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


def test_dashboard_empty(client):
    """Dashboard with no commitments returns empty sections."""
    r = client.get("/commitments/dashboard", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["total_open"] == 0
    assert data["priority_ranked"] == []
    assert data["by_objective"] == []
    assert data["ungrouped"] == []


def test_dashboard_priority_ranked_first(client):
    """Items with priority_order appear in priority_ranked, sorted by rank."""
    # Create 3 items, 2 with priority
    client.post("/commitments/open", json={"title": "Task A", "priority_order": 2}, headers=HEADERS)
    client.post("/commitments/open", json={"title": "Task B", "priority_order": 1}, headers=HEADERS)
    client.post("/commitments/open", json={"title": "Task C"}, headers=HEADERS)

    r = client.get("/commitments/dashboard", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()

    assert data["total_open"] == 3
    assert len(data["priority_ranked"]) == 2
    # Task B should be first (priority 1), Task A second (priority 2)
    assert data["priority_ranked"][0]["title"] == "Task B"
    assert data["priority_ranked"][1]["title"] == "Task A"
    # Task C should be in ungrouped (no priority, no objective)
    ungrouped_titles = []
    for group in data["ungrouped"]:
        for c in group["commitments"]:
            ungrouped_titles.append(c["title"])
    assert "Task C" in ungrouped_titles


def test_dashboard_grouped_by_objective(client):
    """Items linked to objectives appear in by_objective section."""
    # Create an objective
    obj_r = client.post(
        "/objectives/create",
        json={"title": "Increase Revenue", "year": 2026},
        headers=HEADERS,
    )
    obj_id = obj_r.json()["id"]

    # Create commitments
    c1 = client.post("/commitments/open", json={"title": "Close Acme deal"}, headers=HEADERS)
    c1_id = c1.json()["id"]
    client.post("/commitments/open", json={"title": "Unlinked task"}, headers=HEADERS)

    # Link c1 to the objective
    client.post(
        "/objectives/link",
        json={"objective_id": obj_id, "commitment_id": c1_id},
        headers=HEADERS,
    )

    r = client.get("/commitments/dashboard", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()

    assert data["total_open"] == 2
    assert len(data["by_objective"]) == 1
    assert data["by_objective"][0]["objective_title"] == "Increase Revenue"
    assert data["by_objective"][0]["objective_id"] == obj_id
    assert len(data["by_objective"][0]["commitments"]) == 1
    assert data["by_objective"][0]["commitments"][0]["title"] == "Close Acme deal"

    # Unlinked task should be in ungrouped
    ungrouped_titles = []
    for group in data["ungrouped"]:
        for c in group["commitments"]:
            ungrouped_titles.append(c["title"])
    assert "Unlinked task" in ungrouped_titles


def test_dashboard_ungrouped_by_urgency(client):
    """Items without priority or objective are grouped by urgency."""
    client.post("/commitments/open", json={"title": "Fire!", "urgency": "INCIDENT"}, headers=HEADERS)
    client.post("/commitments/open", json={"title": "Soon thing", "urgency": "SOON"}, headers=HEADERS)
    client.post("/commitments/open", json={"title": "Admin stuff", "urgency": "ADMIN"}, headers=HEADERS)

    r = client.get("/commitments/dashboard", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()

    assert data["total_open"] == 3
    assert len(data["priority_ranked"]) == 0
    assert len(data["by_objective"]) == 0

    # Should have groups for INCIDENT, SOON, ADMIN
    labels = [g["group_label"] for g in data["ungrouped"]]
    assert "INCIDENT" in labels
    assert "SOON" in labels
    assert "ADMIN" in labels

    # INCIDENT should come before SOON which should come before ADMIN
    assert labels.index("INCIDENT") < labels.index("SOON")
    assert labels.index("SOON") < labels.index("ADMIN")


def test_dashboard_closed_items_excluded(client):
    """Closed commitments do not appear in the dashboard."""
    c_r = client.post("/commitments/open", json={"title": "Will close"}, headers=HEADERS)
    c_id = c_r.json()["id"]
    client.post("/commitments/open", json={"title": "Still open"}, headers=HEADERS)

    # Close one
    client.post("/commitments/close", json={"commitment_id": c_id}, headers=HEADERS)

    r = client.get("/commitments/dashboard", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()

    assert data["total_open"] == 1
    all_titles = []
    for c in data["priority_ranked"]:
        all_titles.append(c["title"])
    for group in data["by_objective"]:
        for c in group["commitments"]:
            all_titles.append(c["title"])
    for group in data["ungrouped"]:
        for c in group["commitments"]:
            all_titles.append(c["title"])
    assert "Still open" in all_titles
    assert "Will close" not in all_titles


def test_dashboard_no_duplicates(client):
    """Each commitment appears exactly once even if linked to multiple objectives."""
    # Create two objectives
    obj1 = client.post("/objectives/create", json={"title": "Obj 1", "year": 2026}, headers=HEADERS)
    obj2 = client.post("/objectives/create", json={"title": "Obj 2", "year": 2026}, headers=HEADERS)
    obj1_id = obj1.json()["id"]
    obj2_id = obj2.json()["id"]

    # Create a commitment and link to both
    c_r = client.post("/commitments/open", json={"title": "Multi-linked"}, headers=HEADERS)
    c_id = c_r.json()["id"]
    client.post("/objectives/link", json={"objective_id": obj1_id, "commitment_id": c_id}, headers=HEADERS)
    client.post("/objectives/link", json={"objective_id": obj2_id, "commitment_id": c_id}, headers=HEADERS)

    r = client.get("/commitments/dashboard", headers=HEADERS)
    data = r.json()

    assert data["total_open"] == 1
    # Should appear in exactly one objective group (the first linked one)
    total_items = 0
    for group in data["by_objective"]:
        total_items += len(group["commitments"])
    for group in data["ungrouped"]:
        total_items += len(group["commitments"])
    total_items += len(data["priority_ranked"])
    assert total_items == 1


# ---------------------------------------------------------------------------
# Formatted Task List (/tasks)
# ---------------------------------------------------------------------------


def test_tasks_empty(client):
    """GET /tasks with no commitments returns just the count line."""
    r = client.get("/tasks", headers=HEADERS)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert "0 open tasks" in r.text


def test_tasks_priority_execution(client):
    """GET /tasks shows Priority Execution section for items with 'Priority N.' in description."""
    client.post(
        "/commitments/open",
        json={"title": "Alpha task", "description": "Priority 2. Second priority", "person": "Matteo"},
        headers=HEADERS,
    )
    client.post(
        "/commitments/open",
        json={"title": "Beta task", "description": "Priority 1. Top priority"},
        headers=HEADERS,
    )

    r = client.get("/tasks", headers=HEADERS)
    assert r.status_code == 200
    text = r.text
    assert "Priority Execution" in text
    # Beta (Priority 1) should come before Alpha (Priority 2)
    assert text.index("Beta task") < text.index("Alpha task")
    assert "1. Beta task" in text
    assert "2. Alpha task" in text
    # Check person/due formatting
    assert "(Matteo," in text


def test_tasks_initiatives_section(client):
    """GET /tasks shows Initiatives section with tasks grouped under initiative names."""
    # Create an initiative
    ir = client.post("/initiatives/create", json={"title": "Cloud Migration"}, headers=HEADERS)
    init_id = ir.json()["id"]

    # Create commitments and link them
    cr1 = client.post(
        "/commitments/open",
        json={"title": "Set up VPC", "person": "Harneet Kaur"},
        headers=HEADERS,
    )
    c1_id = cr1.json()["id"]
    cr2 = client.post(
        "/commitments/open",
        json={"title": "Migrate databases"},
        headers=HEADERS,
    )
    c2_id = cr2.json()["id"]

    client.post("/initiatives/link", json={"initiative_id": init_id, "commitment_id": c1_id}, headers=HEADERS)
    client.post("/initiatives/link", json={"initiative_id": init_id, "commitment_id": c2_id}, headers=HEADERS)

    r = client.get("/tasks", headers=HEADERS)
    assert r.status_code == 200
    text = r.text
    assert "Initiatives" in text
    assert "Cloud Migration" in text
    assert "Set up VPC" in text
    assert "Migrate databases" in text
    assert "(Harneet Kaur," in text


def test_tasks_everything_else_section(client):
    """GET /tasks puts unlinked items in Everything Else section."""
    client.post(
        "/commitments/open",
        json={"title": "Plan India trip", "person": "Brian Stokes"},
        headers=HEADERS,
    )

    r = client.get("/tasks", headers=HEADERS)
    assert r.status_code == 200
    text = r.text
    assert "Everything Else" in text
    assert "Plan India trip" in text
    assert "(Brian Stokes," in text


def test_tasks_three_section_order(client):
    """GET /tasks shows sections in correct order: Priority Execution > Initiatives > Everything Else."""
    # Unlinked task for Everything Else
    client.post(
        "/commitments/open",
        json={"title": "Regular task"},
        headers=HEADERS,
    )
    # Priority item
    client.post(
        "/commitments/open",
        json={"title": "Top item", "description": "Priority 1. Do first"},
        headers=HEADERS,
    )
    # Initiative with linked commitment
    ir = client.post("/initiatives/create", json={"title": "Big Project"}, headers=HEADERS)
    init_id = ir.json()["id"]
    cr = client.post("/commitments/open", json={"title": "Sub-task for project"}, headers=HEADERS)
    c_id = cr.json()["id"]
    client.post("/initiatives/link", json={"initiative_id": init_id, "commitment_id": c_id}, headers=HEADERS)

    r = client.get("/tasks", headers=HEADERS)
    text = r.text
    assert text.index("Priority Execution") < text.index("Initiatives")
    assert text.index("Initiatives") < text.index("Everything Else")


def test_tasks_sort_within_section(client):
    """Tasks within Everything Else are sorted by urgency then alphabetical."""
    client.post(
        "/commitments/open",
        json={"title": "Zebra task", "urgency": "NOW"},
        headers=HEADERS,
    )
    client.post(
        "/commitments/open",
        json={"title": "Alpha task", "urgency": "SOMEDAY"},
        headers=HEADERS,
    )

    r = client.get("/tasks", headers=HEADERS)
    text = r.text
    assert "Everything Else" in text
    # NOW should sort before SOMEDAY
    assert text.index("Zebra task") < text.index("Alpha task")


def test_tasks_person_due_format(client):
    """Tasks show (person, due date) or em-dashes when missing."""
    client.post(
        "/commitments/open",
        json={"title": "No details task"},
        headers=HEADERS,
    )

    r = client.get("/tasks", headers=HEADERS)
    text = r.text
    # Missing person and date should show em-dashes
    assert "(\u2014, \u2014)" in text


# ---------------------------------------------------------------------------
# Initiative CRUD tests
# ---------------------------------------------------------------------------


def test_create_initiative(client):
    """POST /initiatives/create creates an initiative."""
    r = client.post(
        "/initiatives/create",
        json={"title": "Cloud Migration", "description": "Move to AWS"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Cloud Migration"
    assert data["description"] == "Move to AWS"
    assert data["status"] == "ACTIVE"


def test_list_initiatives(client):
    """GET /initiatives/list returns all initiatives."""
    client.post("/initiatives/create", json={"title": "Init A"}, headers=HEADERS)
    client.post("/initiatives/create", json={"title": "Init B"}, headers=HEADERS)

    r = client.get("/initiatives/list", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2


def test_update_initiative(client):
    """POST /initiatives/update modifies an initiative."""
    cr = client.post("/initiatives/create", json={"title": "Old Title"}, headers=HEADERS)
    init_id = cr.json()["id"]

    r = client.post(
        "/initiatives/update",
        json={"initiative_id": init_id, "title": "New Title", "status": "COMPLETED"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["title"] == "New Title"
    assert r.json()["status"] == "COMPLETED"


def test_get_initiative(client):
    """GET /initiatives/get returns a single initiative."""
    cr = client.post("/initiatives/create", json={"title": "Solo"}, headers=HEADERS)
    init_id = cr.json()["id"]

    r = client.get(f"/initiatives/get?initiative_id={init_id}", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["title"] == "Solo"


def test_get_initiative_not_found(client):
    """GET /initiatives/get returns 404 for missing initiative."""
    r = client.get("/initiatives/get?initiative_id=00000000-0000-0000-0000-000000000000", headers=HEADERS)
    assert r.status_code == 404


def test_seed_initiatives(client):
    """POST /initiatives/seed creates initiatives that don't exist yet."""
    r = client.post(
        "/initiatives/seed",
        json={"titles": ["Alpha", "Beta", "Gamma"]},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    assert {d["title"] for d in data} == {"Alpha", "Beta", "Gamma"}

    # Calling again with overlapping titles should only create new ones
    r2 = client.post(
        "/initiatives/seed",
        json={"titles": ["Beta", "Delta"]},
        headers=HEADERS,
    )
    assert r2.status_code == 200
    data2 = r2.json()
    assert len(data2) == 1
    assert data2[0]["title"] == "Delta"

    # Total should be 4
    r3 = client.get("/initiatives/list", headers=HEADERS)
    assert len(r3.json()) == 4


# ---------------------------------------------------------------------------
# Initiative-Commitment Link tests
# ---------------------------------------------------------------------------


def test_link_commitment_to_initiative(client):
    """POST /initiatives/link links a commitment to an initiative."""
    ir = client.post("/initiatives/create", json={"title": "Migration"}, headers=HEADERS)
    init_id = ir.json()["id"]
    cr = client.post("/commitments/open", json={"title": "Set up VPC"}, headers=HEADERS)
    c_id = cr.json()["id"]

    r = client.post(
        "/initiatives/link",
        json={"initiative_id": init_id, "commitment_id": c_id, "rationale": "Infra work"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["initiative_id"] == init_id
    assert r.json()["commitment_id"] == c_id
    assert r.json()["rationale"] == "Infra work"


def test_link_commitment_by_title(client):
    """POST /initiatives/link resolves commitment by title."""
    ir = client.post("/initiatives/create", json={"title": "Talent"}, headers=HEADERS)
    init_id = ir.json()["id"]
    cr = client.post("/commitments/open", json={"title": "Write welcome note to Deepak"}, headers=HEADERS)
    c_id = cr.json()["id"]

    r = client.post(
        "/initiatives/link",
        json={"initiative_id": init_id, "commitment_title": "welcome note to Deepak"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["commitment_id"] == c_id
    assert r.json()["initiative_id"] == init_id


def test_link_commitment_by_title_no_match(client):
    """POST /initiatives/link returns 404 when title doesn't match."""
    ir = client.post("/initiatives/create", json={"title": "Talent"}, headers=HEADERS)
    init_id = ir.json()["id"]

    r = client.post(
        "/initiatives/link",
        json={"initiative_id": init_id, "commitment_title": "nonexistent task xyz"},
        headers=HEADERS,
    )
    assert r.status_code == 404


def test_link_commitment_by_title_ambiguous(client):
    """POST /initiatives/link returns 409 when title matches multiple."""
    ir = client.post("/initiatives/create", json={"title": "Talent"}, headers=HEADERS)
    init_id = ir.json()["id"]
    client.post("/commitments/open", json={"title": "Review code for Alpha"}, headers=HEADERS)
    client.post("/commitments/open", json={"title": "Review code for Beta"}, headers=HEADERS)

    r = client.post(
        "/initiatives/link",
        json={"initiative_id": init_id, "commitment_title": "Review code"},
        headers=HEADERS,
    )
    assert r.status_code == 409
    assert "candidates" in r.json()["detail"]


def test_link_commitment_no_id_or_title(client):
    """POST /initiatives/link returns 422 when neither ID nor title provided."""
    ir = client.post("/initiatives/create", json={"title": "Talent"}, headers=HEADERS)
    init_id = ir.json()["id"]

    r = client.post(
        "/initiatives/link",
        json={"initiative_id": init_id},
        headers=HEADERS,
    )
    assert r.status_code == 422


def test_unlink_commitment_from_initiative(client):
    """POST /initiatives/unlink removes a link."""
    ir = client.post("/initiatives/create", json={"title": "Migration"}, headers=HEADERS)
    init_id = ir.json()["id"]
    cr = client.post("/commitments/open", json={"title": "Set up VPC"}, headers=HEADERS)
    c_id = cr.json()["id"]

    client.post(
        "/initiatives/link",
        json={"initiative_id": init_id, "commitment_id": c_id},
        headers=HEADERS,
    )
    r = client.post(
        "/initiatives/unlink",
        json={"initiative_id": init_id, "commitment_id": c_id},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["detail"] == "Link removed"


def test_list_initiative_links(client):
    """GET /initiatives/links returns links for an initiative."""
    ir = client.post("/initiatives/create", json={"title": "Migration"}, headers=HEADERS)
    init_id = ir.json()["id"]
    cr = client.post("/commitments/open", json={"title": "Task A"}, headers=HEADERS)
    c_id = cr.json()["id"]

    client.post(
        "/initiatives/link",
        json={"initiative_id": init_id, "commitment_id": c_id},
        headers=HEADERS,
    )
    r = client.get(f"/initiatives/links?initiative_id={init_id}", headers=HEADERS)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_list_commitment_initiatives(client):
    """GET /commitments/initiatives returns initiative links for a commitment."""
    ir = client.post("/initiatives/create", json={"title": "Migration"}, headers=HEADERS)
    init_id = ir.json()["id"]
    cr = client.post("/commitments/open", json={"title": "Task A"}, headers=HEADERS)
    c_id = cr.json()["id"]

    client.post(
        "/initiatives/link",
        json={"initiative_id": init_id, "commitment_id": c_id},
        headers=HEADERS,
    )
    r = client.get(f"/commitments/initiatives?commitment_id={c_id}", headers=HEADERS)
    assert r.status_code == 200
    assert len(r.json()) == 1
