# Tasks: INCIDENT Urgency Level

## Task 1: Add INCIDENT to SQLAlchemy Model
- **File:** `app/models.py`
- **Action:** Add `INCIDENT = "INCIDENT"` as the first value in the `Urgency` enum class
- **Acceptance:** The enum ordering is INCIDENT, NOW, SOON, SCHEDULED, SOMEDAY, ADMIN

## Task 2: Add INCIDENT to Pydantic Schema
- **File:** `app/schemas.py`
- **Action:** Add `INCIDENT = "INCIDENT"` as the first value in the Pydantic `Urgency` enum
- **Acceptance:** Schema mirrors the SQLAlchemy enum ordering

## Task 3: Create Alembic Migration
- **File:** `alembic/versions/002_add_incident_urgency.py`
- **Action:** Write migration that adds `INCIDENT` to the PostgreSQL `urgency` enum type before `NOW`
- **SQL:** `ALTER TYPE urgency ADD VALUE IF NOT EXISTS 'INCIDENT' BEFORE 'NOW'`
- **Acceptance:** Migration runs without error; downgrade is a no-op

## Task 4: Update OpenAPI Spec
- **File:** `openapi.yaml`
- **Action:** Add `INCIDENT` to all 4 urgency enum references
- **Acceptance:** All urgency enums in the spec include INCIDENT as the first value

## Task 5: Update Documentation
- **Files:** `specification.md`, `architecture.md`, `graph.md`
- **Action:** Add INCIDENT to urgency tables, update migration chain, update ER diagram
- **Acceptance:** All docs reflect the new urgency level

## Task 6: Write Tests
- **File:** `tests/test_commitments.py`
- **Action:** Add 3 tests: create with INCIDENT urgency, update to INCIDENT, query by INCIDENT
- **Acceptance:** All 3 new tests pass; all existing tests still pass

## Task 7: Verify and Submit
- **Action:** Run `pytest -v`, commit, push, create PR
- **Acceptance:** All tests pass, PR created with clean diff
