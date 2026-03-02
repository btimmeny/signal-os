# Feature: Objective-Commitment Linking

## Motivation

Strategic objectives need to be connected to the action items (commitments) that drive them forward. This feature creates a many-to-many relationship between objectives and commitments, with an optional rationale explaining why a specific action supports a given goal. This enables questions like "what actions are driving this objective?" and "which objectives does this task support?"

## Data Model

**Table: `objective_commitment_links`**

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, default uuid4 |
| `objective_id` | UUID | FK -> strategic_objectives.id CASCADE, NOT NULL, INDEX |
| `commitment_id` | UUID | FK -> commitments.id CASCADE, NOT NULL |
| `rationale` | TEXT | NULLABLE |
| `created_at` | TIMESTAMPTZ | NOT NULL |

**Unique constraint:** `(objective_id, commitment_id)` -- prevents duplicate links.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/objectives/link` | Link a commitment to an objective (idempotent) |
| POST | `/objectives/unlink` | Remove a link |
| GET | `/objectives/links` | List all commitments linked to an objective |
| GET | `/commitments/objectives` | List all objectives linked to a commitment |

## Service Layer

**File:** `app/services/objective_links.py`

- `link_commitment(db, *, objective_id, commitment_id, rationale)` -- Create or update link (idempotent)
- `unlink_commitment(db, *, objective_id, commitment_id)` -- Remove link
- `list_links_for_objective(db, *, objective_id)` -- All links for an objective
- `list_links_for_commitment(db, *, commitment_id)` -- All links for a commitment

## Migration

**File:** `alembic/versions/007_add_objective_commitment_links.py`

Creates the `objective_commitment_links` table with foreign keys and unique constraint.

## Tests

- `test_link_commitment_to_objective` -- Create a link with rationale
- `test_list_links_for_objective` -- List commitments linked to an objective
- `test_list_objectives_for_commitment` -- List objectives linked to a commitment
- `test_unlink_commitment` -- Remove a link and verify
- `test_link_idempotent` -- Linking same pair twice updates rationale, doesn't duplicate
- `test_link_not_found` -- 404 when objective or commitment doesn't exist

## Design Decisions

- **Idempotent linking:** Re-linking the same pair updates the rationale instead of failing, making it safe to call from AI agents that may repeat actions
- **CASCADE deletes:** Deleting an objective or commitment automatically removes the link
- **Bidirectional queries:** Both "what actions drive this objective?" and "which objectives does this action support?" are first-class queries
- **Rationale field:** Optional text explaining why this action supports the objective, useful for status report generation
