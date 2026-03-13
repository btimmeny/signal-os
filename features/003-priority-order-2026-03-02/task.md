# Tasks: Priority Ordering

## Task 1: Add priority_order Column to Model
- **File:** `app/models.py`
- **Action:** Add `priority_order = Column(Integer, nullable=True)` to `Commitment`
- **Acceptance:** Column exists on the model, nullable

## Task 2: Update Pydantic Schemas
- **File:** `app/schemas.py`
- **Action:** Add `priority_order` to open/update/response schemas; create `CommitmentSetPriorityRequest`
- **Acceptance:** All schemas include `priority_order`; new request schema validates `commitment_id` and `priority_order`

## Task 3: Create Alembic Migration
- **File:** `alembic/versions/004_add_priority_order.py`
- **Action:** Add nullable integer `priority_order` column to `commitments` table
- **Acceptance:** Migration runs cleanly up and down

## Task 4: Implement Reordering Logic
- **File:** `app/services/commitments.py`
- **Action:** Add `_reorder_priorities()`, `_compact_priorities()`, `set_priority()`, `list_priorities()`
- **Acceptance:** Setting priority at position N shifts existing items; priorities are contiguous (no gaps)

## Task 5: Update open_commitment and update_commitment
- **File:** `app/services/commitments.py`
- **Action:** Pass `priority_order` through in `open_commitment()` and `update_commitment()`
- **Acceptance:** Creating/updating a commitment can set its priority_order

## Task 6: Add API Endpoints
- **File:** `app/main.py`
- **Action:** Add `POST /commitments/set_priority` and `GET /commitments/priorities` routes
- **Acceptance:** Both endpoints respond correctly with proper status codes

## Task 7: Update OpenAPI Spec
- **File:** `openapi.yaml`
- **Action:** Add `priority_order` to schemas, add new endpoint definitions
- **Acceptance:** Spec is valid and includes both new endpoints

## Task 8: Update Documentation
- **Files:** `specification.md`, `architecture.md`, `graph.md`
- **Action:** Add data model field, functional requirements, endpoint table entries, migration chain
- **Acceptance:** All docs reflect the new feature

## Task 9: Write Tests
- **File:** `tests/test_commitments.py`
- **Action:** Add 5 tests covering create, set, reorder, list, and update priority
- **Acceptance:** All 5 new tests pass; all existing tests still pass

## Task 10: Verify and Submit
- **Action:** Run `pytest -v`, commit, push, create PR
- **Acceptance:** All tests pass, PR created
