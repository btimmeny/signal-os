# Feature: INCIDENT Urgency Level

## Summary

Adds `INCIDENT` as the highest-priority value in the `Urgency` enum, above `NOW`. This allows commitments to be tagged as production-breaking, urgent incidents that need immediate attention.

## Motivation

When something is urgent and breaking in production today, existing urgency levels (`NOW`, `SOON`, `SCHEDULED`, `SOMEDAY`) don't adequately convey the severity. `INCIDENT` provides a distinct top-priority classification that separates true production emergencies from normal high-priority work.

## Changes

### Modified Files

| File | Change |
|------|--------|
| `app/models.py` | Added `INCIDENT = "INCIDENT"` to `Urgency` enum (first position) |
| `app/schemas.py` | Added `INCIDENT = "INCIDENT"` to Pydantic `Urgency` enum (first position) |
| `openapi.yaml` | Updated all 4 urgency enum references to include `INCIDENT` |
| `specification.md` | Updated urgency field table and urgency levels description |
| `architecture.md` | Updated migration chain and project structure |
| `graph.md` | Updated entity relationship diagram urgency enum values |
| `tests/test_commitments.py` | Added 3 new tests |

### New Files

| File | Purpose |
|------|---------|
| `alembic/versions/002_add_incident_urgency.py` | Alembic migration to add `INCIDENT` to PostgreSQL `urgency` enum type |
| `features/incident-urgency/feature.md` | This file |

## Database Migration

**Migration 002** adds the `INCIDENT` value to the PostgreSQL `urgency` enum type:

```sql
ALTER TYPE urgency ADD VALUE IF NOT EXISTS 'INCIDENT' BEFORE 'NOW'
```

The downgrade is a no-op because PostgreSQL does not support removing values from enum types.

## API Impact

No new endpoints. The `INCIDENT` value is available everywhere `urgency` is accepted:

- `POST /commitments/open` -- Create a commitment with `"urgency": "INCIDENT"`
- `POST /commitments/update` -- Update an existing commitment's urgency to `INCIDENT`
- `GET /commitments/query?urgency=INCIDENT` -- Filter commitments by incident urgency

## Urgency Levels (Updated)

| Level | Description |
|-------|-------------|
| **INCIDENT** | Urgent, breaking in production right now |
| **NOW** | Immediate action required |
| **SOON** | Within the next few days |
| **SCHEDULED** | Has a specific due date |
| **SOMEDAY** | No time pressure |

## Tests Added

| Test | Description |
|------|-------------|
| `test_open_with_incident_urgency` | Create a commitment with `urgency=INCIDENT` and verify it persists |
| `test_update_urgency_to_incident` | Update an existing commitment's urgency to `INCIDENT` |
| `test_query_by_incident_urgency` | Query commitments filtered by `urgency=INCIDENT` returns only incident items |

## PR

- PR #2: https://github.com/btimmeny/signal-os/pull/2
