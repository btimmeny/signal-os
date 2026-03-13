# Feature 014 — Initiatives & 3-Section Task Format

**Date:** 2026-03-13

## Motivation

Add "initiatives" as a first-class entity so every commitment can be linked
to a strategic initiative. When creating a new commitment, the GPT should
check existing initiatives, confirm a match, and link — or prompt the user to
create a new initiative. The `/tasks` output is reformatted into exactly three
sections: **Priority Execution**, **Initiatives**, **Everything Else**.

## Changes

### New Database Tables

| Table | Purpose |
|---|---|
| `initiatives` | Stores initiatives (id, title, description, status, timestamps) |
| `initiative_commitment_links` | Many-to-many join between initiatives and commitments |

**Migration:** `alembic/versions/010_add_initiatives.py`

### New Models (`app/models.py`)

- `InitiativeStatus` enum: ACTIVE, COMPLETED, DEFERRED, CANCELLED
- `Initiative` ORM model
- `InitiativeCommitmentLink` ORM model (join table)
- `Commitment.initiative_links` relationship added

### New Schemas (`app/schemas.py`)

- `InitiativeCreateRequest`, `InitiativeUpdateRequest`, `InitiativeResponse`
- `InitiativeLinkRequest`, `InitiativeLinkResponse`

### New Services

- `app/services/initiatives.py` — CRUD: create, update, list, get
- `app/services/initiative_links.py` — link, unlink, list links

### New API Endpoints (`app/main.py`)

| Method | Path | Description |
|---|---|---|
| POST | `/initiatives/create` | Create a new initiative |
| POST | `/initiatives/update` | Update an initiative |
| GET | `/initiatives/list` | List initiatives (optional status filter) |
| GET | `/initiatives/get` | Get single initiative by ID |
| POST | `/initiatives/link` | Link commitment to initiative |
| POST | `/initiatives/unlink` | Unlink commitment from initiative |
| GET | `/initiatives/links` | List commitments linked to initiative |
| GET | `/commitments/initiatives` | List initiatives linked to commitment |

### Reformatted `/tasks` Output

The `format_dashboard_text()` function was rewritten to produce exactly
three sections:

1. **Priority Execution** — commitments whose description contains
   "Priority N." (extracted via regex)
2. **Initiatives** — commitments whose title starts with "Initiative:"
3. **Everything Else** — all remaining open commitments

Each task line: `Title (person, due date)` with em-dashes for missing fields.

Sort order within each section:
1. Priority number (for Priority Execution)
2. Urgency (INCIDENT > NOW > SOON > SCHEDULED > SOMEDAY > ADMIN)
3. Due date (earliest first)
4. Alphabetical by title

### Updated GPT Instructions (`openapi-gpt.yaml`)

- Full GPT behaviour rules added to `info.description`
- Initiative matching workflow: check existing initiatives before creating
  commitments, confirm with user, link or create new
- Three-section rendering rules enforced
- Language normalization and phrase disambiguation rules
- New initiative endpoint schemas and paths added

## Tests

- 78 total tests (was 70, added 15 new, replaced 7 old section tests)
- New tests cover:
  - Priority Execution section (priority number extraction, ordering)
  - Initiatives section (title prefix matching)
  - Everything Else section (catch-all)
  - Three-section ordering
  - Sort within section (urgency ordering)
  - Person/due date formatting (em-dash fallback)
  - Initiative CRUD (create, list, update, get, not-found)
  - Initiative-commitment linking (link, unlink, list links both directions)
