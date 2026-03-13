# Feature 015: Initiative-Grouped Rendering

**Date:** 2026-03-13

## Motivation

The `/tasks` endpoint previously treated initiatives as flat list items based on
a title prefix ("Initiative: ..."). This made it impossible to see which tasks
belonged to which initiative. Users want tasks **grouped under** their parent
initiative, using the `InitiativeCommitmentLink` join table as the source of
truth.

Additionally, the 10 core initiatives should be seeded into the datastore so
they persist across sessions and evolve over time without being recreated.

## Changes

### `app/services/commitments.py` — `format_dashboard_text()`

Rewrote the Initiatives section rendering:

- **Old:** Checked if a commitment title started with `"Initiative:"` and
  rendered it as a flat bullet item.
- **New:** Queries all ACTIVE `Initiative` records, then for each one queries
  `InitiativeCommitmentLink` to find linked open commitments. Renders each
  initiative as a **header** with linked tasks indented beneath using `  bullet`.
  Empty initiatives (no linked open tasks) are omitted.

Output format:

```
Priority Execution
1. Task (person, date)

Initiatives
Initiative Name 1
  * linked task (person, date)
  * linked task (person, date)

Initiative Name 2
  * linked task (person, date)

Everything Else
* unlinked task (person, date)
```

### `app/services/initiatives.py` — `seed_initiatives()`

New function that accepts a list of initiative titles and creates only those
that do not already exist (case-insensitive match). Prevents duplicate creation
on repeated calls.

### `app/schemas.py` — `InitiativeSeedRequest`

New Pydantic schema for the seed endpoint request body.

### `app/main.py` — `POST /initiatives/seed`

New endpoint that calls `seed_initiatives()` and returns the list of newly
created initiatives.

### `openapi-gpt.yaml`

- Added `InitiativeSeedRequest` schema.
- Added `POST /initiatives/seed` endpoint.
- GPT instructions already include initiative linking workflow guidance
  (from Feature 014).

### `tests/test_commitments.py`

- Updated `test_tasks_initiatives_section` to create an initiative, link
  commitments, and verify grouped rendering with initiative name as header.
- Updated `test_tasks_three_section_order` to use initiative linking instead
  of title-prefix approach.
- Updated `test_tasks_everything_else_section` docstring for clarity.
- Added `test_seed_initiatives` to verify seed endpoint creates new
  initiatives, skips duplicates, and returns correct counts.

## 10 Predefined Initiatives

1. Current Devin Commitments
2. Next Generation Devin Commitments
3. Current UMA Commitments
4. Agent Swarm
5. Event Bus
6. Data Ingest
7. Data Egress
8. Data Factory
9. Knowledge Layer
10. Build our Talent

These should be seeded via `POST /initiatives/seed` after deployment.

## Migration

No database migration required. This feature only changes rendering logic and
adds a new endpoint that uses existing tables.

## Tests

All 79 tests pass (1 new test added for seed endpoint, 3 existing tests updated).
