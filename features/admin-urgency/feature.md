# Feature: ADMIN Urgency Level

## Summary

Adds `ADMIN` as the lowest-priority value in the `Urgency` enum, below `SOMEDAY`. This represents "get it done when you can" tasks -- administrative housekeeping items with no time pressure that should be handled whenever capacity allows.

## Motivation

Some commitments are purely administrative -- rotating keys, cleaning up logs, updating docs. They don't have urgency or deadlines, but still need to be tracked. `ADMIN` provides a distinct lowest-priority classification that separates these background tasks from even `SOMEDAY` items.

## Changes

### Modified Files

| File | Change |
|------|--------|
| `app/models.py` | Added `ADMIN = "ADMIN"` to `Urgency` enum (last position) |
| `app/schemas.py` | Added `ADMIN = "ADMIN"` to Pydantic `Urgency` enum (last position) |
| `openapi.yaml` | Updated all 4 urgency enum references to include `ADMIN` |
| `specification.md` | Updated urgency field table and urgency levels description |
| `architecture.md` | Updated migration chain and project structure |
| `graph.md` | Updated entity relationship diagram urgency enum values |
| `tests/test_commitments.py` | Added 3 new tests |

### New Files

| File | Purpose |
|------|---------|
| `alembic/versions/003_add_admin_urgency.py` | Alembic migration to add `ADMIN` to PostgreSQL `urgency` enum type |
| `features/admin-urgency/feature.md` | This file |

## Database Migration

**Migration 003** adds the `ADMIN` value to the PostgreSQL `urgency` enum type:

```sql
ALTER TYPE urgency ADD VALUE IF NOT EXISTS 'ADMIN' AFTER 'SOMEDAY'
```

The downgrade is a no-op because PostgreSQL does not support removing values from enum types.

## API Impact

No new endpoints. The `ADMIN` value is available everywhere `urgency` is accepted:

- `POST /commitments/open` -- Create a commitment with `"urgency": "ADMIN"`
- `POST /commitments/update` -- Update an existing commitment's urgency to `ADMIN`
- `GET /commitments/query?urgency=ADMIN` -- Filter commitments by admin urgency

## Urgency Levels (Updated)

| Level | Priority | Description |
|-------|----------|-------------|
| **INCIDENT** | Highest | Urgent, breaking in production right now |
| **NOW** | High | Immediate action required |
| **SOON** | Medium | Within the next few days |
| **SCHEDULED** | Normal | Has a specific due date |
| **SOMEDAY** | Low | No time pressure |
| **ADMIN** | Lowest | Get it done when you can |

## Tests Added

| Test | Description |
|------|-------------|
| `test_open_with_admin_urgency` | Create a commitment with `urgency=ADMIN` and verify it persists |
| `test_update_urgency_to_admin` | Update an existing commitment's urgency to `ADMIN` |
| `test_query_by_admin_urgency` | Query commitments filtered by `urgency=ADMIN` returns only admin items |
