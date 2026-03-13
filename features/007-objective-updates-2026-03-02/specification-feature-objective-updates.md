# Feature: Objective Updates

## Motivation

Strategic objectives need general commentary that isn't tied to a specific action item. A user might say "I had a great meeting with the board about this objective" or "market conditions have shifted" -- these updates inform status reports but don't belong on any particular commitment. This feature provides a way to attach timestamped notes directly to objectives.

## Data Model

**Table: `objective_updates`**

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, default uuid4 |
| `objective_id` | UUID | FK -> strategic_objectives.id CASCADE, NOT NULL, INDEX |
| `body` | TEXT | NOT NULL |
| `author` | VARCHAR(256) | NULLABLE |
| `created_at` | TIMESTAMPTZ | NOT NULL |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/objectives/update_note` | Add general commentary to an objective |
| GET | `/objectives/updates` | List all updates for an objective (oldest first) |

## Service Layer

**File:** `app/services/objective_updates.py`

- `add_update(db, *, objective_id, body, author)` -- Add a timestamped update (validates objective exists)
- `list_updates(db, *, objective_id)` -- List all updates, ordered oldest first (validates objective exists)

## Migration

**File:** `alembic/versions/008_add_objective_updates.py`

Creates the `objective_updates` table with foreign key to `strategic_objectives`.

## Tests

- `test_add_objective_update` -- Add an update with body and author
- `test_list_objective_updates` -- List multiple updates in order
- `test_objective_update_not_found` -- 404 when objective doesn't exist
- `test_objective_update_empty_body_rejected` -- 422 for empty body

## Design Decisions

- **Follows CommitmentComment pattern:** Same structure as commitment comments (body, author, created_at) for consistency
- **Separate from commitment comments:** Objective updates are general commentary on the objective itself, not on a specific action item
- **Used by status reporting:** The status data gathering endpoint includes objective updates within the requested period, feeding into status report generation
- **Author is optional:** Supports both attributed and anonymous updates
- **Body validation:** Empty bodies are rejected (422) since an update with no content is meaningless
