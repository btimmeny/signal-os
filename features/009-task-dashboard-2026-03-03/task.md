# Tasks: Task Dashboard

## Task 1: Implement get_dashboard Service
- **File:** `app/services/commitments.py`
- **Action:** Add `get_dashboard(db)` that fetches non-CLOSED commitments, separates priority-ranked items, groups by objective, and groups remaining by urgency
- **Acceptance:** Returns dict with `total_open`, `priority_ranked`, `by_objective`, `ungrouped`; every non-CLOSED item appears exactly once

## Task 2: Add Dashboard API Endpoint
- **File:** `app/main.py`
- **Action:** Add `GET /commitments/dashboard` route that calls `get_dashboard()` and serializes response
- **Acceptance:** Endpoint returns 200 with organized JSON; closed items excluded

## Task 3: Add GPT Anti-Hallucination Instructions
- **File:** `openapi.yaml`
- **Action:** Add instruction block to top-level description and endpoint description enforcing grouped format; add redirect warnings on list endpoints
- **Acceptance:** OpenAPI spec explicitly prohibits flat numbered lists and directs GPT to use dashboard

## Task 4: Update Documentation
- **Files:** `specification.md`, `architecture.md`, `graph.md`
- **Action:** Add FR-34, FR-35, endpoint entry, service function docs
- **Acceptance:** All docs reflect the new feature

## Task 5: Write Tests
- **File:** `tests/test_commitments.py`
- **Action:** Add 6 tests for empty, priority ranking, objective grouping, urgency grouping, closed exclusion, no duplicates
- **Acceptance:** All 6 new tests pass; all existing tests still pass

## Task 6: Verify and Submit
- **Action:** Run `pytest -v`, commit, push, create PR
- **Acceptance:** All tests pass, PR created
