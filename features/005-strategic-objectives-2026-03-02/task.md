# Tasks: Strategic Objectives

## Task 1: Create ObjectiveStatus Enum and StrategicObjective Model
- **File:** `app/models.py`
- **Action:** Add `ObjectiveStatus` enum (ACTIVE, COMPLETED, DEFERRED, CANCELLED) and `StrategicObjective` ORM model
- **Acceptance:** Model has id, title, description, year, status, created_at, updated_at

## Task 2: Create Pydantic Schemas
- **File:** `app/schemas.py`
- **Action:** Add `ObjectiveCreateRequest`, `ObjectiveUpdateRequest`, `ObjectiveResponse`
- **Acceptance:** Create requires title+year; update requires objective_id; response includes all fields

## Task 3: Create Alembic Migration
- **File:** `alembic/versions/006_add_strategic_objectives.py`
- **Action:** Create `objective_status` enum and `strategic_objectives` table with indexes
- **Acceptance:** Migration runs cleanly up and down

## Task 4: Implement Objectives Service
- **File:** `app/services/objectives.py` (new)
- **Action:** Add `create_objective()`, `update_objective()`, `get_objective()`, `list_objectives()` with year/status filters
- **Acceptance:** CRUD operations work correctly; filters return expected results

## Task 5: Add API Endpoints
- **File:** `app/main.py`
- **Action:** Add `POST /objectives/create`, `POST /objectives/update`, `GET /objectives/list`, `GET /objectives/get`
- **Acceptance:** All endpoints respond correctly with proper status codes

## Task 6: Update OpenAPI Spec
- **File:** `openapi.yaml`
- **Action:** Add objective schemas and endpoint definitions
- **Acceptance:** Spec is valid

## Task 7: Update Documentation
- **Files:** `specification.md`, `architecture.md`, `graph.md`
- **Action:** Add Objective entity, functional requirements, endpoint entries
- **Acceptance:** All docs reflect the new feature

## Task 8: Write Tests
- **File:** `tests/test_objectives.py`
- **Action:** Add 6 tests for create, list, update, get, not-found, and status filter
- **Acceptance:** All 6 new tests pass; all existing tests still pass

## Task 9: Verify and Submit
- **Action:** Run `pytest -v`, commit, push, create PR
- **Acceptance:** All tests pass, PR created
