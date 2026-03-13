# Tasks: ADMIN Urgency Level

## Task 1: Add ADMIN to SQLAlchemy Model
- **File:** `app/models.py`
- **Action:** Add `ADMIN = "ADMIN"` as the last value in the `Urgency` enum class
- **Acceptance:** The enum ordering is INCIDENT, NOW, SOON, SCHEDULED, SOMEDAY, ADMIN

## Task 2: Add ADMIN to Pydantic Schema
- **File:** `app/schemas.py`
- **Action:** Add `ADMIN = "ADMIN"` as the last value in the Pydantic `Urgency` enum
- **Acceptance:** Schema mirrors the SQLAlchemy enum ordering

## Task 3: Create Alembic Migration
- **File:** `alembic/versions/003_add_admin_urgency.py`
- **Action:** Write migration that adds `ADMIN` to the PostgreSQL `urgency` enum type after `SOMEDAY`
- **SQL:** `ALTER TYPE urgency ADD VALUE IF NOT EXISTS 'ADMIN' AFTER 'SOMEDAY'`
- **Acceptance:** Migration runs without error; downgrade is a no-op

## Task 4: Update OpenAPI Spec
- **File:** `openapi.yaml`
- **Action:** Add `ADMIN` to all 4 urgency enum references as the last value
- **Acceptance:** All urgency enums include ADMIN

## Task 5: Update Documentation
- **Files:** `specification.md`, `architecture.md`, `graph.md`
- **Action:** Add ADMIN to urgency tables, update migration chain, update ER diagram
- **Acceptance:** All docs reflect the new urgency level

## Task 6: Write Tests
- **File:** `tests/test_commitments.py`
- **Action:** Add 3 tests: create with ADMIN, update to ADMIN, query by ADMIN
- **Acceptance:** All 3 new tests pass; all existing tests still pass

## Task 7: Verify and Submit
- **Action:** Run `pytest -v`, commit, push, create PR
- **Acceptance:** All tests pass, PR created
