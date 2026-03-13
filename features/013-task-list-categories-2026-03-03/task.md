# Tasks: Task List Categories

## Task 1: Add Keycap Emoji Helpers
- **File:** `app/services/commitments.py`
- **Action:** Add `_KEYCAP_DIGITS` list and `_keycap(n)` helper for numbered emoji rendering
- **Acceptance:** `_keycap(1)` returns the keycap 1 emoji; handles 1-9+

## Task 2: Add Due Date Suffix Helper
- **File:** `app/services/commitments.py`
- **Action:** Add `_due_suffix(c)` that returns "-- Due Mon DD" when `due_at` is set, empty string otherwise
- **Acceptance:** Formats due dates inline; returns empty for commitments without due dates

## Task 3: Rewrite format_dashboard_text
- **File:** `app/services/commitments.py`
- **Action:** Replace three-section rendering with six-category waterfall (first match wins): Ranked Execution, Immediate, Time-Bound, Strategy, HR, Administration
- **Acceptance:** Each task appears in exactly one category; empty categories omitted; Ranked uses keycap emoji, others use bullets

## Task 4: Remove _format_task_details
- **File:** `app/services/commitments.py`
- **Action:** Remove sub-detail bullet rendering in favor of clean compact format
- **Acceptance:** Tasks show title + inline due date only, no sub-bullets

## Task 5: Replace /tasks Tests
- **File:** `tests/test_commitments.py`
- **Action:** Remove 4 old tests, add 7 new tests covering each category and overall ordering
- **Acceptance:** All 7 new tests pass; total test count is correct

## Task 6: Verify and Submit
- **Action:** Run `pytest -v`, commit, push, create PR
- **Acceptance:** All tests pass, PR created
