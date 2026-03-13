# Feature: Strategic Objectives

## Motivation

Signal OS tracks individual commitments (action items), but lacks the ability to organize them under higher-level goals. Strategic objectives represent annual goals that commitments drive toward, providing the "why" behind individual tasks. This enables users to say "here are my objectives for the year" and later align every action to those objectives.

## Data Model

**Table: `strategic_objectives`**

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, default uuid4 |
| `title` | VARCHAR(512) | NOT NULL, INDEX |
| `description` | TEXT | NULLABLE |
| `year` | INTEGER | NOT NULL, INDEX |
| `status` | ENUM (objective_status) | NOT NULL, default ACTIVE |
| `created_at` | TIMESTAMPTZ | NOT NULL |
| `updated_at` | TIMESTAMPTZ | NOT NULL |

**Enum: `objective_status`** -- ACTIVE, COMPLETED, DEFERRED, CANCELLED

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/objectives/create` | Create a new objective (title, year required) |
| POST | `/objectives/update` | Update fields by objective_id |
| GET | `/objectives/list` | List objectives (optional year, status filters) |
| GET | `/objectives/get` | Get a single objective by ID |

## Service Layer

**File:** `app/services/objectives.py`

- `create_objective(db, *, title, description, year, status)` -- Create with defaults
- `update_objective(db, *, objective_id, **fields)` -- Partial update
- `get_objective(db, *, objective_id)` -- Single lookup
- `list_objectives(db, *, year, status)` -- Filtered list

## Migration

**File:** `alembic/versions/006_add_strategic_objectives.py`

Creates the `strategic_objectives` table and `objective_status` enum type.

## Tests

- `test_create_objective` -- Create and verify response fields
- `test_list_objectives` -- List all and filter by year
- `test_update_objective` -- Update title and status
- `test_get_objective` -- Get by ID
- `test_get_objective_not_found` -- 404 for missing ID
- `test_list_objectives_by_status` -- Filter by status

## Design Decisions

- Objectives are mutable (update-in-place, not versioned) -- keeps it simple for a personal tool
- Year is an integer field rather than a date range, matching the user's mental model of "annual objectives"
- Status defaults to ACTIVE on creation
- No cascade relationships to commitments -- linking is handled by the separate objective-commitment-linking feature
