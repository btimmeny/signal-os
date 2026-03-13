# Tasks: Task Detail Rendering

## Task 1: Add _format_task_details Helper
- **File:** `app/services/commitments.py`
- **Action:** Add `_format_task_details(c)` that builds detail sub-bullet lines for Person, Org, Urgency, Status, Due, Channel, Note
- **Acceptance:** Only renders fields that have values; formats due date as Mon DD, YYYY

## Task 2: Update format_dashboard_text
- **File:** `app/services/commitments.py`
- **Action:** Render task titles in bold; append detail lines from `_format_task_details()` as indented sub-bullets
- **Acceptance:** Each task shows bold title followed by detail lines

## Task 3: Update Existing Tests
- **File:** `tests/test_commitments.py`
- **Action:** Update existing `/tasks` tests to match bold title format (`**title**`)
- **Acceptance:** Existing tests pass with updated assertions

## Task 4: Add Detail Fields Test
- **File:** `tests/test_commitments.py`
- **Action:** Add `test_tasks_detail_fields` creating a commitment with all fields and verifying each detail line
- **Acceptance:** Test verifies Person, Org, Urgency, Status, Due, Channel, Note sub-bullets

## Task 5: Verify and Submit
- **Action:** Run `pytest -v`, commit, push, create PR
- **Acceptance:** All tests pass, PR created
