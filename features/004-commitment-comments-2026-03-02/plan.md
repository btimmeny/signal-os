# Plan: Commitment Comments

## Objective

Add timestamped comments to commitments so users can track history, meeting notes, progress updates, and context on each action item.

## Prerequisites

- Access to the Signal OS repository
- Features 001-003 already merged

## Steps

### 1. Create the ORM Model

1. Open `app/models.py`
2. Add `CommitmentComment` model with columns: `id` (UUID PK), `commitment_id` (UUID FK with CASCADE), `body` (TEXT NOT NULL), `author` (VARCHAR(256) NULLABLE), `created_at` (TIMESTAMPTZ)
3. Add `comments` relationship to `Commitment` model with `lazy="select"`

### 2. Create Pydantic Schemas

1. Open `app/schemas.py`
2. Add `CommentCreateRequest` with `commitment_id`, `body` (min_length=1), `author` (optional)
3. Add `CommentResponse` with all fields plus `from_orm` support

### 3. Create Database Migration

1. Create `alembic/versions/005_add_commitment_comments.py`
2. Create `commitment_comments` table with FK to `commitments.id` (CASCADE)
3. Add index on `commitment_id`

### 4. Implement Service Layer

1. Create `app/services/comments.py`
2. Add `add_comment(db, *, commitment_id, body, author)` — validates commitment exists, creates comment
3. Add `list_comments(db, *, commitment_id)` — validates commitment exists, returns comments oldest-first

### 5. Add API Endpoints

1. Open `app/main.py`
2. Add `POST /commitments/comment` — calls `add_comment()`, returns 404 if commitment not found
3. Add `GET /commitments/comments` — calls `list_comments()`, returns 404 if commitment not found

### 6. Update OpenAPI Spec

1. Add `CommentCreateRequest` and `Comment` schemas
2. Add both endpoint definitions

### 7. Update Documentation

1. Update `specification.md` — add Comment entity (4.3), FR-18, FR-19, endpoint entries
2. Update `architecture.md` — project structure, service layer, migration chain
3. Update `graph.md` — ER diagram, API route map, module dependency graph

### 8. Register Model in Test Config

1. Open `tests/conftest.py`
2. Import `CommitmentComment` model so test DB creates the table

### 9. Write Tests

Add 7 tests:
1. `test_add_comment` — Add comment with author, verify fields
2. `test_list_comments` — Multiple comments, verify ordering
3. `test_comment_on_nonexistent_commitment` — 404
4. `test_list_comments_nonexistent_commitment` — 404
5. `test_comment_empty_body_rejected` — 422
6. `test_comments_empty_for_new_commitment` — Empty list
7. `test_comments_deleted_with_commitment` — Comments persist after closing

### 10. Verify and Submit

1. Run `pytest -v` — all tests must pass
2. Commit, push, create PR
