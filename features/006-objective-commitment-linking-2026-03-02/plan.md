# Plan: Objective-Commitment Linking

## Objective

Create a many-to-many relationship between strategic objectives and commitments, with optional rationale explaining why an action supports a goal.

## Prerequisites

- Access to the Signal OS repository
- Feature 005 (Strategic Objectives) already merged

## Steps

### 1. Create the ORM Model

1. Open `app/models.py`
2. Add `ObjectiveCommitmentLink` model with: `id` (UUID PK), `objective_id` (UUID FK CASCADE), `commitment_id` (UUID FK CASCADE), `rationale` (TEXT nullable), `created_at`
3. Add unique constraint on `(objective_id, commitment_id)`

### 2. Create Pydantic Schemas

1. Open `app/schemas.py`
2. Add `ObjectiveLinkRequest` with `objective_id`, `commitment_id`, `rationale` (optional)
3. Add `ObjectiveLinkResponse` with all fields

### 3. Create Database Migration

1. Create `alembic/versions/007_add_objective_commitment_links.py`
2. Create `objective_commitment_links` table with FKs and unique constraint

### 4. Implement Service Layer

1. Create `app/services/objective_links.py`
2. Add `link_commitment()` — idempotent (re-linking updates rationale)
3. Add `unlink_commitment()` — remove link
4. Add `list_links_for_objective()` — all links for an objective
5. Add `list_links_for_commitment()` — all links for a commitment

### 5. Add API Endpoints

1. Add `POST /objectives/link`, `POST /objectives/unlink`
2. Add `GET /objectives/links`, `GET /commitments/objectives`

### 6. Update OpenAPI Spec and Documentation

1. Update `openapi.yaml` with schemas and endpoints
2. Update `specification.md`, `architecture.md`, `graph.md`

### 7. Write Tests

Add 6 tests:
1. `test_link_commitment_to_objective` — Create link with rationale
2. `test_list_links_for_objective` — List commitments linked to objective
3. `test_list_objectives_for_commitment` — List objectives for commitment
4. `test_unlink_commitment` — Remove link
5. `test_link_idempotent` — Re-linking updates rationale
6. `test_link_not_found` — 404 for missing objective/commitment

### 8. Verify and Submit

1. Run `pytest -v` — all tests must pass
2. Commit, push, create PR
