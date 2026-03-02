"""Tests for strategic objectives, linking, updates, and status reports."""

HEADERS = {"X-API-Key": "test-key"}


# ---------------------------------------------------------------------------
# Feature 1: Strategic Objectives CRUD
# ---------------------------------------------------------------------------

def test_create_objective(client):
    """Create a strategic objective and verify response."""
    r = client.post(
        "/objectives/create",
        json={"title": "Increase revenue by 20%", "year": 2026, "description": "Top-line growth target"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Increase revenue by 20%"
    assert data["year"] == 2026
    assert data["status"] == "ACTIVE"
    assert data["description"] == "Top-line growth target"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_list_objectives(client):
    """List objectives, optionally filtered by year."""
    client.post(
        "/objectives/create",
        json={"title": "Obj A", "year": 2026},
        headers=HEADERS,
    )
    client.post(
        "/objectives/create",
        json={"title": "Obj B", "year": 2025},
        headers=HEADERS,
    )

    # List all
    r = client.get("/objectives/list", headers=HEADERS)
    assert r.status_code == 200
    assert len(r.json()) == 2

    # Filter by year
    r2 = client.get("/objectives/list?year=2026", headers=HEADERS)
    assert r2.status_code == 200
    items = r2.json()
    assert len(items) == 1
    assert items[0]["title"] == "Obj A"


def test_update_objective(client):
    """Update an objective's fields."""
    r = client.post(
        "/objectives/create",
        json={"title": "Original title", "year": 2026},
        headers=HEADERS,
    )
    oid = r.json()["id"]

    r2 = client.post(
        "/objectives/update",
        json={"objective_id": oid, "title": "Updated title", "status": "COMPLETED"},
        headers=HEADERS,
    )
    assert r2.status_code == 200
    assert r2.json()["title"] == "Updated title"
    assert r2.json()["status"] == "COMPLETED"


def test_get_objective(client):
    """Get a single objective by ID."""
    r = client.post(
        "/objectives/create",
        json={"title": "Get me", "year": 2026},
        headers=HEADERS,
    )
    oid = r.json()["id"]

    r2 = client.get(f"/objectives/get?objective_id={oid}", headers=HEADERS)
    assert r2.status_code == 200
    assert r2.json()["title"] == "Get me"


def test_get_objective_not_found(client):
    """Getting a non-existent objective returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.get(f"/objectives/get?objective_id={fake_id}", headers=HEADERS)
    assert r.status_code == 404


def test_list_objectives_by_status(client):
    """Filter objectives by status."""
    r1 = client.post(
        "/objectives/create",
        json={"title": "Active one", "year": 2026},
        headers=HEADERS,
    )
    r2 = client.post(
        "/objectives/create",
        json={"title": "Deferred one", "year": 2026, "status": "DEFERRED"},
        headers=HEADERS,
    )

    r = client.get("/objectives/list?status=ACTIVE", headers=HEADERS)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["title"] == "Active one"


# ---------------------------------------------------------------------------
# Feature 2: Objective-Commitment Linking
# ---------------------------------------------------------------------------

def _create_objective_and_commitment(client):
    """Helper to create an objective and a commitment."""
    o = client.post(
        "/objectives/create",
        json={"title": "Strategic goal", "year": 2026},
        headers=HEADERS,
    ).json()
    c = client.post(
        "/commitments/open",
        json={"title": "Action item for goal"},
        headers=HEADERS,
    ).json()
    return o["id"], c["id"]


def test_link_commitment_to_objective(client):
    """Link a commitment to an objective."""
    oid, cid = _create_objective_and_commitment(client)

    r = client.post(
        "/objectives/link",
        json={"objective_id": oid, "commitment_id": cid, "rationale": "Drives revenue growth"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["objective_id"] == oid
    assert data["commitment_id"] == cid
    assert data["rationale"] == "Drives revenue growth"


def test_list_links_for_objective(client):
    """List all commitments linked to an objective."""
    oid, cid = _create_objective_and_commitment(client)

    client.post(
        "/objectives/link",
        json={"objective_id": oid, "commitment_id": cid},
        headers=HEADERS,
    )

    r = client.get(f"/objectives/links?objective_id={oid}", headers=HEADERS)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["commitment_id"] == cid


def test_list_objectives_for_commitment(client):
    """List all objectives linked to a commitment."""
    oid, cid = _create_objective_and_commitment(client)

    client.post(
        "/objectives/link",
        json={"objective_id": oid, "commitment_id": cid},
        headers=HEADERS,
    )

    r = client.get(f"/commitments/objectives?commitment_id={cid}", headers=HEADERS)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["objective_id"] == oid


def test_unlink_commitment(client):
    """Unlink a commitment from an objective."""
    oid, cid = _create_objective_and_commitment(client)

    client.post(
        "/objectives/link",
        json={"objective_id": oid, "commitment_id": cid},
        headers=HEADERS,
    )

    r = client.post(
        "/objectives/unlink",
        json={"objective_id": oid, "commitment_id": cid},
        headers=HEADERS,
    )
    assert r.status_code == 200

    # Verify no links remain
    r2 = client.get(f"/objectives/links?objective_id={oid}", headers=HEADERS)
    assert len(r2.json()) == 0


def test_link_idempotent(client):
    """Linking the same commitment twice doesn't create a duplicate."""
    oid, cid = _create_objective_and_commitment(client)

    client.post(
        "/objectives/link",
        json={"objective_id": oid, "commitment_id": cid, "rationale": "First"},
        headers=HEADERS,
    )
    client.post(
        "/objectives/link",
        json={"objective_id": oid, "commitment_id": cid, "rationale": "Updated"},
        headers=HEADERS,
    )

    r = client.get(f"/objectives/links?objective_id={oid}", headers=HEADERS)
    items = r.json()
    assert len(items) == 1
    assert items[0]["rationale"] == "Updated"


def test_link_not_found(client):
    """Linking with a non-existent objective or commitment returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"

    r = client.post(
        "/objectives/link",
        json={"objective_id": fake_id, "commitment_id": fake_id},
        headers=HEADERS,
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Feature 3: Objective Updates (general commentary)
# ---------------------------------------------------------------------------

def test_add_objective_update(client):
    """Add an update to an objective."""
    r = client.post(
        "/objectives/create",
        json={"title": "Growth target", "year": 2026},
        headers=HEADERS,
    )
    oid = r.json()["id"]

    r2 = client.post(
        "/objectives/update_note",
        json={"objective_id": oid, "body": "Met with VP Sales, pipeline looking strong", "author": "Brian"},
        headers=HEADERS,
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["body"] == "Met with VP Sales, pipeline looking strong"
    assert data["author"] == "Brian"
    assert data["objective_id"] == oid


def test_list_objective_updates(client):
    """List all updates for an objective."""
    r = client.post(
        "/objectives/create",
        json={"title": "Obj for updates", "year": 2026},
        headers=HEADERS,
    )
    oid = r.json()["id"]

    client.post(
        "/objectives/update_note",
        json={"objective_id": oid, "body": "First note"},
        headers=HEADERS,
    )
    client.post(
        "/objectives/update_note",
        json={"objective_id": oid, "body": "Second note", "author": "Alice"},
        headers=HEADERS,
    )

    r2 = client.get(f"/objectives/updates?objective_id={oid}", headers=HEADERS)
    assert r2.status_code == 200
    items = r2.json()
    assert len(items) == 2
    assert items[0]["body"] == "First note"
    assert items[1]["body"] == "Second note"
    assert items[1]["author"] == "Alice"


def test_objective_update_not_found(client):
    """Adding an update to a non-existent objective returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.post(
        "/objectives/update_note",
        json={"objective_id": fake_id, "body": "Nope"},
        headers=HEADERS,
    )
    assert r.status_code == 404


def test_objective_update_empty_body_rejected(client):
    """Empty update body is rejected."""
    r = client.post(
        "/objectives/create",
        json={"title": "Obj for empty test", "year": 2026},
        headers=HEADERS,
    )
    oid = r.json()["id"]

    r2 = client.post(
        "/objectives/update_note",
        json={"objective_id": oid, "body": ""},
        headers=HEADERS,
    )
    assert r2.status_code == 422


# ---------------------------------------------------------------------------
# Feature 4: Status Reports
# ---------------------------------------------------------------------------

def test_create_status_report(client):
    """Create a status report."""
    r = client.post(
        "/status/report",
        json={
            "period_type": "WEEKLY",
            "period_start": "2026-02-23T00:00:00Z",
            "period_end": "2026-03-01T23:59:59Z",
            "body": "This week we made progress on objectives A and B.",
        },
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["period_type"] == "WEEKLY"
    assert "This week" in data["body"]
    assert "id" in data


def test_list_status_reports(client):
    """List status reports, filtered by period type."""
    client.post(
        "/status/report",
        json={
            "period_type": "WEEKLY",
            "period_start": "2026-02-23T00:00:00Z",
            "period_end": "2026-03-01T23:59:59Z",
            "body": "Weekly report",
        },
        headers=HEADERS,
    )
    client.post(
        "/status/report",
        json={
            "period_type": "MONTHLY",
            "period_start": "2026-02-01T00:00:00Z",
            "period_end": "2026-02-28T23:59:59Z",
            "body": "Monthly report",
        },
        headers=HEADERS,
    )

    # All
    r = client.get("/status/reports", headers=HEADERS)
    assert r.status_code == 200
    assert len(r.json()) == 2

    # Filtered
    r2 = client.get("/status/reports?period_type=WEEKLY", headers=HEADERS)
    assert r2.status_code == 200
    items = r2.json()
    assert len(items) == 1
    assert items[0]["period_type"] == "WEEKLY"


def test_get_status_report(client):
    """Get a single report by ID."""
    r = client.post(
        "/status/report",
        json={
            "period_type": "QUARTERLY",
            "period_start": "2026-01-01T00:00:00Z",
            "period_end": "2026-03-31T23:59:59Z",
            "body": "Q1 summary",
        },
        headers=HEADERS,
    )
    rid = r.json()["id"]

    r2 = client.get(f"/status/report?report_id={rid}", headers=HEADERS)
    assert r2.status_code == 200
    assert r2.json()["body"] == "Q1 summary"


def test_gather_status_data(client):
    """Gather status data aggregates objectives, links, comments, and updates."""
    # Create objective
    obj = client.post(
        "/objectives/create",
        json={"title": "Revenue growth", "year": 2026},
        headers=HEADERS,
    ).json()

    # Create commitment and link
    commit = client.post(
        "/commitments/open",
        json={"title": "Close deal with Acme"},
        headers=HEADERS,
    ).json()
    client.post(
        "/objectives/link",
        json={"objective_id": obj["id"], "commitment_id": commit["id"], "rationale": "Big deal"},
        headers=HEADERS,
    )

    # Add a comment on the commitment
    client.post(
        "/commitments/comment",
        json={"commitment_id": commit["id"], "body": "Had follow-up call"},
        headers=HEADERS,
    )

    # Add an objective update
    client.post(
        "/objectives/update_note",
        json={"objective_id": obj["id"], "body": "Pipeline is strong"},
        headers=HEADERS,
    )

    # Gather data for a wide period
    r = client.post(
        "/status/data",
        json={
            "period_type": "WEEKLY",
            "period_start": "2020-01-01T00:00:00Z",
            "period_end": "2030-12-31T23:59:59Z",
        },
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()

    # Verify objectives with linked commitments
    assert len(data["objectives"]) >= 1
    obj_data = next(o for o in data["objectives"] if o["objective_id"] == obj["id"])
    assert len(obj_data["linked_commitments"]) == 1
    assert obj_data["linked_commitments"][0]["title"] == "Close deal with Acme"
    assert len(obj_data["linked_commitments"][0]["period_comments"]) == 1

    # Verify objective updates
    assert len(obj_data["period_updates"]) == 1
    assert obj_data["period_updates"][0]["body"] == "Pipeline is strong"

    # Verify commitment activity
    assert len(data["commitments_opened"]) >= 1


def test_gather_status_data_empty_period(client):
    """Gathering data for a period with no activity returns empty lists."""
    r = client.post(
        "/status/data",
        json={
            "period_type": "WEEKLY",
            "period_start": "2020-01-01T00:00:00Z",
            "period_end": "2020-01-07T23:59:59Z",
        },
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["commitments_opened"] == []
    assert data["commitments_closed"] == []
