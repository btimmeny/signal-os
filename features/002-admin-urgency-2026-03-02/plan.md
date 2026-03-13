# Plan: ADMIN Urgency Level

## Objective

Add `ADMIN` as the lowest-priority urgency level (below `SOMEDAY`) representing "get it done when you can" administrative tasks.

## Prerequisites

- Access to the Signal OS repository
- INCIDENT urgency feature (001) already merged

## Steps

### 1. Update the Data Model

1. Open `app/models.py`
2. Add `ADMIN = "ADMIN"` as the **last** value in the `Urgency` enum class (after SOMEDAY)

### 2. Update the Pydantic Schema

1. Open `app/schemas.py`
2. Add `ADMIN = "ADMIN"` as the **last** value in the Pydantic `Urgency` enum

### 3. Create Database Migration

1. Create `alembic/versions/003_add_admin_urgency.py`
2. Use `ALTER TYPE urgency ADD VALUE IF NOT EXISTS 'ADMIN' AFTER 'SOMEDAY'`
3. Downgrade is a no-op

### 4. Update OpenAPI Spec

1. Open `openapi.yaml`
2. Add `ADMIN` to all 4 urgency enum references as the last value

### 5. Update Documentation

1. Update `specification.md` — urgency levels description
2. Update `architecture.md` — migration chain
3. Update `graph.md` — ER diagram urgency enum values

### 6. Write Tests

Add 3 tests to `tests/test_commitments.py`:
1. `test_open_with_admin_urgency` — Create with `urgency=ADMIN`
2. `test_update_urgency_to_admin` — Update urgency to `ADMIN`
3. `test_query_by_admin_urgency` — Filter by `urgency=ADMIN`

### 7. Verify and Submit

1. Run `pytest -v` — all tests must pass
2. Commit, push, create PR
