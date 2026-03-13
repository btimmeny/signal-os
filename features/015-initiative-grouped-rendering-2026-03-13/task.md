# Tasks: Initiative-Grouped Rendering

## Task 1: Rewrite Initiatives Section in format_dashboard_text
- **File:** `app/services/commitments.py`
- **Action:** Replace title-prefix matching with join-table queries: fetch ACTIVE initiatives, query linked open commitments, render as header + indented tasks
- **Acceptance:** Initiatives appear as headers; linked tasks indented with `  *`; empty initiatives omitted

## Task 2: Implement seed_initiatives Service
- **File:** `app/services/initiatives.py`
- **Action:** Add `seed_initiatives(db, titles)` that creates only non-existing initiatives (case-insensitive check)
- **Acceptance:** Idempotent — repeated calls don't create duplicates; returns newly created list

## Task 3: Add InitiativeSeedRequest Schema
- **File:** `app/schemas.py`
- **Action:** Add `InitiativeSeedRequest` with `titles: List[str]`
- **Acceptance:** Schema validates list of strings

## Task 4: Add /initiatives/seed Endpoint
- **File:** `app/main.py`
- **Action:** Add `POST /initiatives/seed` route calling `seed_initiatives()`
- **Acceptance:** Endpoint creates new initiatives and returns them; skips duplicates

## Task 5: Update OpenAPI Spec
- **File:** `openapi-gpt.yaml`
- **Action:** Add `InitiativeSeedRequest` schema and `POST /initiatives/seed` endpoint
- **Acceptance:** Spec is valid

## Task 6: Update Tests
- **File:** `tests/test_commitments.py`
- **Action:** Update initiative section tests to use linking; add `test_seed_initiatives`
- **Acceptance:** All updated and new tests pass

## Task 7: Verify and Submit
- **Action:** Run `pytest -v`, commit, push, create PR
- **Acceptance:** All tests pass, PR created
