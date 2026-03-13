# Plan: Tasks Plain Text Endpoint

## Objective

Add a `GET /tasks` endpoint that returns all non-CLOSED commitments as pre-formatted markdown plain text, preventing GPT from reformatting the output.

## Prerequisites

- Access to the Signal OS repository
- Feature 009 (Task Dashboard) already merged — uses `get_dashboard()` function

## Steps

### 1. Implement Text Formatter

1. Open `app/services/commitments.py`
2. Add `format_dashboard_text(db)` function that:
   - Calls existing `get_dashboard(db)` to get organized data
   - Renders result as markdown with `##` section headings
   - Top Priorities: numbered list (1. 2. 3.)
   - By Objective: objective title as heading, bulleted items
   - By Urgency: urgency label as heading, bulleted items
   - Includes due dates as `(due MMM DD)` suffix
   - Returns a single string

### 2. Add API Endpoint

1. Open `app/main.py`
2. Add `GET /tasks` route returning `PlainTextResponse`
3. Import `PlainTextResponse` from `fastapi.responses`
4. Add docstring instructing AI agents to display text verbatim

### 3. Update OpenAPI Spec

1. Open `openapi.yaml`
2. Replace verbose formatting instructions with: "call `GET /tasks`, display verbatim"
3. Add `/tasks` path with `text/plain` response schema
4. Demote `/commitments/dashboard` to programmatic JSON access

### 4. Update Documentation

1. Update `specification.md` — FR-36, endpoint entry
2. Update `architecture.md` — `format_dashboard_text()` service function
3. Update `graph.md` — `/tasks` route

### 5. Write Tests

Add 4 tests:
1. `test_tasks_empty` — Returns `text/plain` with "0 open tasks"
2. `test_tasks_priority_section` — Priority section with numbering
3. `test_tasks_objective_section` — Objective title as heading
4. `test_tasks_urgency_section` — Urgency label grouping

### 6. Verify and Submit

1. Run `pytest -v` — all tests must pass
2. Commit, push, create PR
