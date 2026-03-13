# Tasks: Initiatives

## Task 1: Create Initiative Models
- **File:** `app/models.py`
- **Action:** Add `InitiativeStatus` enum, `Initiative` model, `InitiativeCommitmentLink` join model, `initiative_links` relationship on Commitment
- **Acceptance:** Both models create tables with correct columns, FKs, and unique constraint

## Task 2: Create Alembic Migration
- **File:** `alembic/versions/010_add_initiatives.py`
- **Action:** Create `initiatives` and `initiative_commitment_links` tables with FKs and unique constraint
- **Acceptance:** Migration runs cleanly up and down

## Task 3: Create Pydantic Schemas
- **File:** `app/schemas.py`
- **Action:** Add initiative create/update/response schemas and link request/response schemas
- **Acceptance:** All schemas validate correctly

## Task 4: Implement Initiative CRUD Service
- **File:** `app/services/initiatives.py` (new)
- **Action:** Add `create_initiative()`, `update_initiative()`, `list_initiatives()`, `get_initiative()`
- **Acceptance:** CRUD operations work; list supports status filter

## Task 5: Implement Initiative Link Service
- **File:** `app/services/initiative_links.py` (new)
- **Action:** Add `link_commitment()` (idempotent), `unlink_commitment()`, `list_links_for_initiative()`, `list_links_for_commitment()`
- **Acceptance:** Idempotent linking; bidirectional queries work

## Task 6: Add CRUD API Endpoints
- **File:** `app/main.py`
- **Action:** Add POST create, POST update, GET list, GET get for initiatives
- **Acceptance:** All endpoints respond correctly

## Task 7: Add Linking API Endpoints
- **File:** `app/main.py`
- **Action:** Add POST link, POST unlink, GET links (for initiative), GET initiatives (for commitment)
- **Acceptance:** All endpoints respond correctly; 404 for missing entities

## Task 8: Rewrite /tasks Three-Section Format
- **File:** `app/services/commitments.py`
- **Action:** Rewrite `format_dashboard_text()` for Priority Execution, Initiatives, Everything Else sections
- **Acceptance:** Three sections render correctly with proper sorting

## Task 9: Update GPT Instructions
- **File:** `openapi-gpt.yaml`
- **Action:** Add initiative schemas, endpoints, and GPT behavior rules for initiative matching
- **Acceptance:** Spec is valid and under ChatGPT limits

## Task 10: Write Tests
- **Files:** `tests/test_commitments.py`
- **Action:** Add tests for initiative CRUD, linking, and three-section rendering
- **Acceptance:** All new tests pass; all existing tests still pass

## Task 11: Verify and Submit
- **Action:** Run `pytest -v`, commit, push, create PR
- **Acceptance:** All tests pass, PR created
