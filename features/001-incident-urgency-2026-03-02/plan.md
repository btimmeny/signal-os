# Plan: INCIDENT Urgency Level

## Objective

Add `INCIDENT` as the highest-priority urgency level (above `NOW`) to the commitment system.

## Prerequisites

- Access to the Signal OS repository
- Python environment with FastAPI, SQLAlchemy, Alembic
- PostgreSQL database (production) / SQLite (tests)

## Steps

### 1. Update the Data Model

1. Open `app/models.py`
2. Add `INCIDENT = "INCIDENT"` as the **first** value in the `Urgency` enum class
3. Verify the enum ordering places INCIDENT above NOW

### 2. Update the Pydantic Schema

1. Open `app/schemas.py`
2. Add `INCIDENT = "INCIDENT"` as the **first** value in the Pydantic `Urgency` enum

### 3. Create Database Migration

1. Create `alembic/versions/002_add_incident_urgency.py`
2. Use `ALTER TYPE urgency ADD VALUE IF NOT EXISTS 'INCIDENT' BEFORE 'NOW'`
3. Downgrade is a no-op (PostgreSQL cannot remove enum values)

### 4. Update OpenAPI Spec

1. Open `openapi.yaml`
2. Find all 4 references to the urgency enum
3. Add `INCIDENT` to each enum list as the first value

### 5. Update Documentation

1. Update `specification.md` — urgency field table and urgency levels description
2. Update `architecture.md` — migration chain and project structure
3. Update `graph.md` — entity relationship diagram urgency enum values

### 6. Write Tests

Add 3 tests to `tests/test_commitments.py`:
1. `test_open_with_incident_urgency` — Create a commitment with `urgency=INCIDENT` and verify
2. `test_update_urgency_to_incident` — Update an existing commitment's urgency to `INCIDENT`
3. `test_query_by_incident_urgency` — Query commitments filtered by `urgency=INCIDENT`

### 7. Verify

1. Run `pytest -v` — all tests must pass
2. Review the migration script for correctness
3. Verify OpenAPI spec is valid

### 8. Submit

1. Commit all changes
2. Push to a feature branch
3. Create a pull request
