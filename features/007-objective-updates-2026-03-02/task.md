# Tasks: Objective Updates

## Task 1: Create ObjectiveUpdate Model
- **File:** `app/models.py`
- **Action:** Add `ObjectiveUpdate` model with `id`, `objective_id` (FK CASCADE), `body`, `author`, `created_at`
- **Acceptance:** Model creates table with correct columns and foreign key

## Task 2: Create Pydantic Schemas
- **File:** `app/schemas.py`
- **Action:** Add `ObjectiveUpdateCreateRequest` (objective_id, body min_length=1, author optional) and `ObjectiveUpdateResponse`
- **Acceptance:** Body validation rejects empty strings; response includes all fields

## Task 3: Create Alembic Migration
- **File:** `alembic/versions/008_add_objective_updates.py`
- **Action:** Create `objective_updates` table with FK CASCADE to strategic_objectives
- **Acceptance:** Migration runs cleanly up and down

## Task 4: Implement Update Service
- **File:** `app/services/objective_updates.py` (new)
- **Action:** Add `add_update()` and `list_updates()` with objective existence validation
- **Acceptance:** Returns None/empty if objective not found; updates ordered oldest-first

## Task 5: Add API Endpoints
- **File:** `app/main.py`
- **Action:** Add `POST /objectives/update_note` and `GET /objectives/updates`
- **Acceptance:** Both endpoints respond correctly; 404 for missing objective

## Task 6: Update OpenAPI Spec and Documentation
- **Files:** `openapi.yaml`, `specification.md`, `architecture.md`, `graph.md`
- **Action:** Add schemas, endpoints, entity docs, migration chain
- **Acceptance:** All specs and docs reflect the new feature

## Task 7: Write Tests
- **File:** `tests/test_objectives.py`
- **Action:** Add 4 tests for add, list, not-found, and empty body rejection
- **Acceptance:** All 4 new tests pass; all existing tests still pass

## Task 8: Verify and Submit
- **Action:** Run `pytest -v`, commit, push, create PR
- **Acceptance:** All tests pass, PR created
