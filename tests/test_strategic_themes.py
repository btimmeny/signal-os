"""Tests for strategic themes: CRUD, seeding, initiative linking, and task rendering."""

from tests.conftest import HEADERS


# ---------------------------------------------------------------------------
# Theme CRUD
# ---------------------------------------------------------------------------

def test_create_theme(client):
    r = client.post(
        "/themes/create",
        json={"title": "AI-Native SDLC", "description": "Transform SDLC with AI"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "AI-Native SDLC"
    assert data["description"] == "Transform SDLC with AI"
    assert data["status"] == "ACTIVE"
    assert "id" in data


def test_list_themes(client):
    client.post("/themes/create", json={"title": "Theme A"}, headers=HEADERS)
    client.post("/themes/create", json={"title": "Theme B"}, headers=HEADERS)

    r = client.get("/themes/list", headers=HEADERS)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2


def test_list_themes_by_status(client):
    client.post("/themes/create", json={"title": "Active Theme"}, headers=HEADERS)
    r2 = client.post("/themes/create", json={"title": "Deferred Theme"}, headers=HEADERS)
    theme_id = r2.json()["id"]
    client.post(
        "/themes/update",
        json={"theme_id": theme_id, "status": "DEFERRED"},
        headers=HEADERS,
    )

    r = client.get("/themes/list?status=ACTIVE", headers=HEADERS)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["title"] == "Active Theme"


def test_update_theme(client):
    r = client.post("/themes/create", json={"title": "Old Title"}, headers=HEADERS)
    theme_id = r.json()["id"]

    r2 = client.post(
        "/themes/update",
        json={"theme_id": theme_id, "title": "New Title", "status": "COMPLETED"},
        headers=HEADERS,
    )
    assert r2.status_code == 200
    assert r2.json()["title"] == "New Title"
    assert r2.json()["status"] == "COMPLETED"


def test_update_theme_not_found(client):
    r = client.post(
        "/themes/update",
        json={"theme_id": "00000000-0000-0000-0000-000000000000", "title": "X"},
        headers=HEADERS,
    )
    assert r.status_code == 404


def test_get_theme(client):
    r = client.post("/themes/create", json={"title": "Get Me"}, headers=HEADERS)
    theme_id = r.json()["id"]

    r2 = client.get(f"/themes/get?theme_id={theme_id}", headers=HEADERS)
    assert r2.status_code == 200
    assert r2.json()["title"] == "Get Me"


def test_get_theme_not_found(client):
    r = client.get(
        "/themes/get?theme_id=00000000-0000-0000-0000-000000000000",
        headers=HEADERS,
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Theme seeding
# ---------------------------------------------------------------------------

def test_seed_themes(client):
    r = client.post(
        "/themes/seed",
        json={
            "themes": [
                {"title": "AI-Native SDLC", "description": "Transform SDLC"},
                {"title": "Agent Infrastructure", "description": "Runtime systems"},
            ]
        },
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["title"] == "AI-Native SDLC"
    assert data[0]["description"] == "Transform SDLC"

    # Seeding again should be idempotent
    r2 = client.post(
        "/themes/seed",
        json={
            "themes": [
                {"title": "AI-Native SDLC"},
                {"title": "Knowledge Platform", "description": "Access firm knowledge"},
            ]
        },
        headers=HEADERS,
    )
    data2 = r2.json()
    assert len(data2) == 1  # Only "Knowledge Platform" is new
    assert data2[0]["title"] == "Knowledge Platform"


# ---------------------------------------------------------------------------
# Initiative-Theme linking
# ---------------------------------------------------------------------------

def test_create_initiative_with_theme(client):
    # Create a theme first
    t = client.post("/themes/create", json={"title": "My Theme"}, headers=HEADERS)
    theme_id = t.json()["id"]

    # Create initiative linked to theme
    r = client.post(
        "/initiatives/create",
        json={"title": "My Initiative", "theme_id": theme_id},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["theme_id"] == theme_id
    assert data["theme_title"] == "My Theme"


def test_create_initiative_without_theme(client):
    r = client.post(
        "/initiatives/create",
        json={"title": "Standalone Initiative"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["theme_id"] is None
    assert data["theme_title"] is None


def test_update_initiative_theme(client):
    # Create theme
    t = client.post("/themes/create", json={"title": "Theme X"}, headers=HEADERS)
    theme_id = t.json()["id"]

    # Create initiative without theme
    r = client.post(
        "/initiatives/create",
        json={"title": "Orphan Initiative"},
        headers=HEADERS,
    )
    init_id = r.json()["id"]

    # Update to link theme
    r2 = client.post(
        "/initiatives/update",
        json={"initiative_id": init_id, "theme_id": theme_id},
        headers=HEADERS,
    )
    assert r2.status_code == 200
    assert r2.json()["theme_id"] == theme_id


# ---------------------------------------------------------------------------
# Initiative focus warning
# ---------------------------------------------------------------------------

def test_initiative_focus_warning(client):
    """Linking >15 tasks to an initiative should return a warning."""
    # Create initiative
    r = client.post(
        "/initiatives/create",
        json={"title": "Overloaded Initiative"},
        headers=HEADERS,
    )
    init_id = r.json()["id"]

    # Create and link 16 commitments
    last_response = None
    for i in range(16):
        c = client.post(
            "/commitments/open",
            json={"title": f"Task {i+1}"},
            headers=HEADERS,
        )
        cid = c.json()["id"]
        last_response = client.post(
            "/initiatives/link",
            json={"initiative_id": init_id, "commitment_id": cid},
            headers=HEADERS,
        )
        assert last_response.status_code == 200

    # After 16th link, the response should contain a warning
    assert "warning" in last_response.json()
    assert "16 active tasks" in last_response.json()["warning"]


# ---------------------------------------------------------------------------
# Tasks rendering with theme hierarchy
# ---------------------------------------------------------------------------

def test_tasks_theme_grouping(client):
    """Tasks should be grouped under Theme > Initiative in /tasks output."""
    # Create a theme
    t = client.post("/themes/create", json={"title": "AI-Native SDLC"}, headers=HEADERS)
    theme_id = t.json()["id"]

    # Create initiative under the theme
    init = client.post(
        "/initiatives/create",
        json={"title": "Devin Commitments", "theme_id": theme_id},
        headers=HEADERS,
    )
    init_id = init.json()["id"]

    # Create a commitment and link to initiative
    c = client.post(
        "/commitments/open",
        json={"title": "Automate SonarQube"},
        headers=HEADERS,
    )
    cid = c.json()["id"]
    client.post(
        "/initiatives/link",
        json={"initiative_id": init_id, "commitment_id": cid},
        headers=HEADERS,
    )

    # Get tasks
    r = client.get("/tasks", headers=HEADERS)
    assert r.status_code == 200
    text = r.text
    assert "AI-Native SDLC" in text
    assert "Devin Commitments" in text
    assert "Automate SonarQube" in text


def test_tasks_unthemed_initiatives(client):
    """Initiatives without a theme should appear under 'Other Initiatives'."""
    # Create initiative without theme
    init = client.post(
        "/initiatives/create",
        json={"title": "Standalone Work"},
        headers=HEADERS,
    )
    init_id = init.json()["id"]

    # Create and link a commitment
    c = client.post(
        "/commitments/open",
        json={"title": "Misc task"},
        headers=HEADERS,
    )
    cid = c.json()["id"]
    client.post(
        "/initiatives/link",
        json={"initiative_id": init_id, "commitment_id": cid},
        headers=HEADERS,
    )

    r = client.get("/tasks", headers=HEADERS)
    assert r.status_code == 200
    text = r.text
    assert "Other Initiatives" in text
    assert "Standalone Work" in text
    assert "Misc task" in text


def test_tasks_multiple_themes(client):
    """Multiple themes with their own initiatives and tasks render properly."""
    # Create two themes
    t1 = client.post("/themes/create", json={"title": "Theme Alpha"}, headers=HEADERS)
    t2 = client.post("/themes/create", json={"title": "Theme Beta"}, headers=HEADERS)
    t1_id = t1.json()["id"]
    t2_id = t2.json()["id"]

    # Create initiatives under each
    i1 = client.post(
        "/initiatives/create",
        json={"title": "Alpha Initiative", "theme_id": t1_id},
        headers=HEADERS,
    )
    i2 = client.post(
        "/initiatives/create",
        json={"title": "Beta Initiative", "theme_id": t2_id},
        headers=HEADERS,
    )
    i1_id = i1.json()["id"]
    i2_id = i2.json()["id"]

    # Create tasks
    c1 = client.post("/commitments/open", json={"title": "Alpha Task"}, headers=HEADERS)
    c2 = client.post("/commitments/open", json={"title": "Beta Task"}, headers=HEADERS)
    c1_id = c1.json()["id"]
    c2_id = c2.json()["id"]

    # Link
    client.post("/initiatives/link", json={"initiative_id": i1_id, "commitment_id": c1_id}, headers=HEADERS)
    client.post("/initiatives/link", json={"initiative_id": i2_id, "commitment_id": c2_id}, headers=HEADERS)

    r = client.get("/tasks", headers=HEADERS)
    text = r.text

    assert "Theme Alpha" in text
    assert "Alpha Initiative" in text
    assert "Alpha Task" in text
    assert "Theme Beta" in text
    assert "Beta Initiative" in text
    assert "Beta Task" in text

    # Alpha should appear before Beta (created first)
    assert text.index("Theme Alpha") < text.index("Theme Beta")
