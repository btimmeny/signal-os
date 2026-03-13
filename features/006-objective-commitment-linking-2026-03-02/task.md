# Tasks: Objective-Commitment Linking

## Task 1: Create ObjectiveCommitmentLink Model
- **File:** `app/models.py`
- **Action:** Add `ObjectiveCommitmentLink` model with FKs to objectives and commitments, unique constraint on (objective_id, commitment_id)
- **Acceptance:** Model creates table with correct columns, FKs, and constraint

## Task 2: Create Pydantic Schemas
- **File:** `app/schemas.py`
- **Action:** Add `ObjectiveLinkRequest` and `ObjectiveLinkResponse`
- **Acceptance:** Request requires objective_id and commitment_id; rationale is optional

## Task 3: Create Alembic Migration
- **File:** `alembic/versions/007_add_objective_commitment_links.py`
- **Action:** Create `objective_commitment_links` table with FKs and unique constraint
- **Acceptance:** Migration runs cleanly up and down

## Task 4: Implement Link Service
- **File:** `app/services/objective_links.py` (new)
- **Action:** Add `link_commitment()` (idempotent), `unlink_commitment()`, `list_links_for_objective()`, `list_links_for_commitment()`
- **Acceptance:** Idempotent linking updates rationale without duplicating; unlink removes cleanly

## Task 5: Add API Endpoints
- **File:** `app/main.py`
- **Action:** Add `POST /objectives/link`, `POST /objectives/unlink`, `GET /objectives/links`, `GET /commitments/objectives`
- **Acceptance:** All endpoints respond correctly; bidirectional queries work

## Task 6: Update OpenAPI Spec
- **File:** `openapi.yaml`
- **Action:** Add link schemas and endpoint definitions
- **Acceptance:** Spec is valid

## Task 7: Update Documentation
- **Files:** `specification.md`, `architecture.md`, `graph.md`
- **Action:** Add link entity, functional requirements, endpoint entries
- **Acceptance:** All docs reflect the new feature

## Task 8: Write Tests
- **File:** `tests/test_objectives.py`
- **Action:** Add 6 tests for link, list, unlink, idempotent, and not-found scenarios
- **Acceptance:** All 6 new tests pass; all existing tests still pass

## Task 9: Verify and Submit
- **Action:** Run `pytest -v`, commit, push, create PR
- **Acceptance:** All tests pass, PR created
