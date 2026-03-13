# Tasks: Commitment Comments

## Task 1: Create CommitmentComment ORM Model
- **File:** `app/models.py`
- **Action:** Add `CommitmentComment` model with `id`, `commitment_id` (FK CASCADE), `body`, `author`, `created_at`; add `comments` relationship to `Commitment`
- **Acceptance:** Model creates table with correct columns and foreign key

## Task 2: Create Pydantic Schemas
- **File:** `app/schemas.py`
- **Action:** Add `CommentCreateRequest` (commitment_id, body min_length=1, author optional) and `CommentResponse`
- **Acceptance:** Body validation rejects empty strings; response includes all fields

## Task 3: Create Alembic Migration
- **File:** `alembic/versions/005_add_commitment_comments.py`
- **Action:** Create `commitment_comments` table with FK CASCADE and index on `commitment_id`
- **Acceptance:** Migration runs cleanly up and down

## Task 4: Implement Comment Service
- **File:** `app/services/comments.py` (new)
- **Action:** Add `add_comment()` and `list_comments()` functions with commitment existence validation
- **Acceptance:** Returns 404 if commitment not found; comments ordered oldest-first

## Task 5: Add API Endpoints
- **File:** `app/main.py`
- **Action:** Add `POST /commitments/comment` and `GET /commitments/comments` routes
- **Acceptance:** Both endpoints respond correctly; 404 for missing commitment

## Task 6: Update OpenAPI Spec
- **File:** `openapi.yaml`
- **Action:** Add `CommentCreateRequest`, `Comment` schemas and endpoint definitions
- **Acceptance:** Spec is valid

## Task 7: Register Model in Test Config
- **File:** `tests/conftest.py`
- **Action:** Import `CommitmentComment` so test DB creates the table
- **Acceptance:** Tests can create comments without migration

## Task 8: Update Documentation
- **Files:** `specification.md`, `architecture.md`, `graph.md`
- **Action:** Add Comment entity, functional requirements, endpoint entries, migration chain
- **Acceptance:** All docs reflect the new feature

## Task 9: Write Tests
- **File:** `tests/test_commitments.py`
- **Action:** Add 7 tests covering add, list, 404s, empty body, empty list, cascade behavior
- **Acceptance:** All 7 new tests pass; all existing tests still pass

## Task 10: Verify and Submit
- **Action:** Run `pytest -v`, commit, push, create PR
- **Acceptance:** All tests pass, PR created
