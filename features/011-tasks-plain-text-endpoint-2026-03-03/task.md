# Tasks: Tasks Plain Text Endpoint

## Task 1: Implement format_dashboard_text
- **File:** `app/services/commitments.py`
- **Action:** Add `format_dashboard_text(db)` that calls `get_dashboard()` and renders markdown with section headings, numbered priorities, and bulleted items
- **Acceptance:** Returns a single plain text string with proper markdown formatting

## Task 2: Add /tasks API Endpoint
- **File:** `app/main.py`
- **Action:** Add `GET /tasks` route returning `PlainTextResponse`; import `PlainTextResponse`
- **Acceptance:** Endpoint returns `text/plain` content type with formatted text

## Task 3: Update OpenAPI Spec
- **File:** `openapi.yaml`
- **Action:** Add `/tasks` path with `text/plain` response; update instructions to "display verbatim"; demote `/commitments/dashboard`
- **Acceptance:** Spec directs GPT to use `/tasks` for display

## Task 4: Update Documentation
- **Files:** `specification.md`, `architecture.md`, `graph.md`
- **Action:** Add FR-36, endpoint entry, service function docs
- **Acceptance:** All docs reflect the new endpoint

## Task 5: Write Tests
- **File:** `tests/test_commitments.py`
- **Action:** Add 4 tests for empty, priority section, objective section, urgency section
- **Acceptance:** All 4 new tests pass; all existing tests still pass

## Task 6: Verify and Submit
- **Action:** Run `pytest -v`, commit, push, create PR
- **Acceptance:** All tests pass, PR created
