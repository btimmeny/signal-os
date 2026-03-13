# Plan: Strategic Objectives

## Objective

Add strategic objectives as a first-class entity — annual goals that commitments drive toward, providing the "why" behind individual tasks.

## Prerequisites

- Access to the Signal OS repository
- Features 001-004 already merged

## Steps

### 1. Create the ORM Model

1. Open `app/models.py`
2. Add `ObjectiveStatus` enum: ACTIVE, COMPLETED, DEFERRED, CANCELLED
3. Add `StrategicObjective` model with columns: `id` (UUID PK), `title` (VARCHAR 512), `description` (TEXT nullable), `year` (INTEGER), `status` (ObjectiveStatus, default ACTIVE), `created_at`, `updated_at`

### 2. Create Pydantic Schemas

1. Open `app/schemas.py`
2. Add `ObjectiveCreateRequest` with `title`, `year` (required), `description`, `status` (optional)
3. Add `ObjectiveUpdateRequest` with `objective_id` (required), all other fields optional
4. Add `ObjectiveResponse` with all fields plus `from_orm` support

### 3. Create Database Migration

1. Create `alembic/versions/006_add_strategic_objectives.py`
2. Create `objective_status` enum type
3. Create `strategic_objectives` table with indexes on `title` and `year`

### 4. Implement Service Layer

1. Create `app/services/objectives.py`
2. Add `create_objective()`, `update_objective()`, `get_objective()`, `list_objectives()`
3. `list_objectives` supports optional `year` and `status` filters

### 5. Add API Endpoints

1. Open `app/main.py`
2. Add `POST /objectives/create`, `POST /objectives/update`, `GET /objectives/list`, `GET /objectives/get`

### 6. Update OpenAPI Spec and Documentation

1. Update `openapi.yaml` with new schemas and endpoints
2. Update `specification.md`, `architecture.md`, `graph.md`

### 7. Write Tests

Add 6 tests:
1. `test_create_objective` — Create and verify fields
2. `test_list_objectives` — List all and filter by year
3. `test_update_objective` — Update title and status
4. `test_get_objective` — Get by ID
5. `test_get_objective_not_found` — 404
6. `test_list_objectives_by_status` — Filter by status

### 8. Verify and Submit

1. Run `pytest -v` — all tests must pass
2. Commit, push, create PR
