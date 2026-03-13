# Tasks: Dashboard GPT Training Fix

## Task 1: Update Top-Level API Description
- **File:** `openapi.yaml`
- **Action:** Add explicit output template showing grouped format; add statement that flat numbered list is WRONG
- **Acceptance:** Top-level description includes format example and prohibition

## Task 2: Update Dashboard Endpoint Description
- **File:** `openapi.yaml`
- **Action:** Add detailed formatting rules with section headings example; emphasize NEVER flatten
- **Acceptance:** Endpoint description includes format rules

## Task 3: Add Redirect Warnings on List Endpoints
- **File:** `openapi.yaml`
- **Action:** Update `/commitments/open` and `/commitments/priorities` descriptions to redirect GPT to dashboard
- **Acceptance:** Both endpoints warn GPT to use dashboard for display

## Task 4: Update Route Docstring
- **File:** `app/main.py`
- **Action:** Update `/commitments/dashboard` route docstring with grouped format example
- **Acceptance:** Docstring matches OpenAPI spec instructions

## Task 5: Verify and Submit
- **Action:** Run `pytest -v` (no functional changes, all existing tests must pass), commit, push, create PR
- **Acceptance:** All tests pass, PR created
