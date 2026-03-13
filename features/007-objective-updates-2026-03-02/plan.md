# Plan: Objective Updates

## Objective

Add timestamped general commentary on strategic objectives — notes not tied to specific commitments, useful for meeting notes, market observations, and strategic shifts.

## Prerequisites

- Access to the Signal OS repository
- Feature 005 (Strategic Objectives) already merged

## Steps

### 1. Create the ORM Model

1. Open `app/models.py`
2. Add `ObjectiveUpdate` model with: `id` (UUID PK), `objective_id` (UUID FK CASCADE), `body` (TEXT NOT NULL), `author` (VARCHAR 256 nullable), `created_at`

### 2. Create Pydantic Schemas

1. Open `app/schemas.py`
2. Add `ObjectiveUpdateCreateRequest` with `objective_id`, `body` (min_length=1), `author` (optional)
3. Add `ObjectiveUpdateResponse` with all fields

### 3. Create Database Migration

1. Create `alembic/versions/008_add_objective_updates.py`
2. Create `objective_updates` table with FK to `strategic_objectives.id` (CASCADE)

### 4. Implement Service Layer

1. Create `app/services/objective_updates.py`
2. Add `add_update(db, *, objective_id, body, author)` — validates objective exists
3. Add `list_updates(db, *, objective_id)` — returns updates oldest-first, validates objective exists

### 5. Add API Endpoints

1. Open `app/main.py`
2. Add `POST /objectives/update_note` — calls `add_update()`
3. Add `GET /objectives/updates` — calls `list_updates()`

### 6. Update OpenAPI Spec and Documentation

1. Update `openapi.yaml` with schemas and endpoints
2. Update `specification.md`, `architecture.md`, `graph.md`

### 7. Write Tests

Add 4 tests:
1. `test_add_objective_update` — Add update with body and author
2. `test_list_objective_updates` — List multiple updates in order
3. `test_objective_update_not_found` — 404 for missing objective
4. `test_objective_update_empty_body_rejected` — 422 for empty body

### 8. Verify and Submit

1. Run `pytest -v` — all tests must pass
2. Commit, push, create PR
