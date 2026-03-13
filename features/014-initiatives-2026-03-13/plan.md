# Plan: Initiatives

## Objective

Add initiatives as a first-class entity with CRUD, commitment linking, and reformat `/tasks` into three sections: Priority Execution, Initiatives, Everything Else.

## Prerequisites

- Access to the Signal OS repository
- Features 001-013 already merged

## Steps

### 1. Create Database Tables

1. Open `app/models.py`
2. Add `InitiativeStatus` enum: ACTIVE, COMPLETED, DEFERRED, CANCELLED
3. Add `Initiative` model with: `id`, `title`, `description`, `status`, `created_at`, `updated_at`
4. Add `InitiativeCommitmentLink` model with: `id`, `initiative_id` (FK), `commitment_id` (FK), `rationale`, `created_at`
5. Add `initiative_links` relationship to `Commitment`

### 2. Create Alembic Migration

1. Create `alembic/versions/010_add_initiatives.py`
2. Create `initiatives` and `initiative_commitment_links` tables
3. Add unique constraint on `(initiative_id, commitment_id)`

### 3. Create Pydantic Schemas

1. Add `InitiativeCreateRequest`, `InitiativeUpdateRequest`, `InitiativeResponse`
2. Add `InitiativeLinkRequest`, `InitiativeLinkResponse`

### 4. Implement Service Layer

1. Create `app/services/initiatives.py` -- CRUD: create, update, list, get
2. Create `app/services/initiative_links.py` -- link, unlink, list links

### 5. Add API Endpoints

1. Add CRUD: `POST /initiatives/create`, `POST /initiatives/update`, `GET /initiatives/list`, `GET /initiatives/get`
2. Add linking: `POST /initiatives/link`, `POST /initiatives/unlink`, `GET /initiatives/links`, `GET /commitments/initiatives`

### 6. Reformat /tasks Output

1. Rewrite `format_dashboard_text()` to produce three sections:
   - Priority Execution: commitments with "Priority N." in description
   - Initiatives: commitments with "Initiative:" title prefix
   - Everything Else: all remaining
2. Sort within sections by priority number, urgency, due date, title

### 7. Update GPT Instructions

1. Update `openapi-gpt.yaml` with initiative endpoints and schemas
2. Add initiative matching workflow to GPT behavior rules
3. Add three-section rendering rules

### 8. Write Tests

Add tests covering:
- Initiative CRUD (create, list, update, get, not-found)
- Initiative-commitment linking (link, unlink, list both directions)
- Three-section /tasks rendering (priority, initiatives, everything else)
- Sort ordering within sections

### 9. Verify and Submit

1. Run `pytest -v` -- all tests must pass
2. Commit, push, create PR
