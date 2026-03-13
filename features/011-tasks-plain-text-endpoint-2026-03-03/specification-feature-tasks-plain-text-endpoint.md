# Tasks Plain Text Endpoint

## Motivation

Despite two rounds of GPT training instruction updates (features 009 and 010), GPT continued to flatten the JSON dashboard response into a numbered list (1-16). The root cause: GPT treats formatting instructions as suggestions, not requirements, and defaults to its own presentation style when given structured JSON data.

The solution is to make flattening impossible by returning **pre-formatted markdown as plain text** instead of JSON. GPT cannot reformat plain text — it can only display it verbatim.

## Feature Summary

New `GET /tasks` endpoint that returns all non-CLOSED commitments as pre-formatted markdown text organized into three sections:

1. **Top Priorities** — Items with `priority_order`, numbered (1. 2. 3. ...)
2. **By Objective** — Remaining items grouped under objective title headings, bulleted
3. **By Urgency** — Ungrouped items sub-grouped by urgency level, bulleted

The response is `text/plain`, not JSON. The OpenAPI spec instructs GPT to call this endpoint and display the text exactly as returned.

## Changes

### Service Layer (`app/services/commitments.py`)

- Added `format_dashboard_text(db)` function that:
  - Calls existing `get_dashboard(db)` to get organized data
  - Renders the result as markdown text with `##` section headings
  - Includes due dates as `(due MMM DD)` suffix where applicable
  - Returns a single string ready for display

### Route (`app/main.py`)

- Added `GET /tasks` route with `PlainTextResponse`
- Docstring instructs AI agents to display the returned text exactly as-is
- Import added: `PlainTextResponse` from `fastapi.responses`

### OpenAPI Spec (`openapi.yaml`)

- **Top-level API description** — Replaced verbose formatting instructions with concise directive: "call `GET /tasks`, display verbatim"
- **New `/tasks` path** — Defined with `text/plain` response schema and instruction to display verbatim
- **`/commitments/dashboard`** — Demoted to "use for programmatic JSON access"; notes that `/tasks` is preferred for display

### Documentation

- **`architecture.md`** — Added `format_dashboard_text()` to service layer listing
- **`specification.md`** — Added FR-36, added `/tasks` to endpoint table
- **`graph.md`** — Added `/tasks` to API route map
- **`features/009-task-dashboard-2026-03-03/feature.md`** — Added `/tasks` endpoint documentation alongside existing `/commitments/dashboard`

## No Migration Required

Read-only endpoint built on top of existing `get_dashboard()`. No schema changes.

## API

### `GET /tasks`

**Response:** `text/plain`

```
**5 open tasks**

## Top Priorities
1. Launch Claude CLI (due Mar 15)
2. Architecture & vTeam Plan

## Revenue Growth
- Close Acme deal (due Mar 20)

## INCIDENT
- Fix production outage

## ADMIN
- Read Cognition article
```

## Tests Added

4 new tests in `tests/test_commitments.py`:

| Test | Description |
|------|-------------|
| `test_tasks_empty` | Returns `text/plain` with "0 open tasks" when no commitments exist |
| `test_tasks_priority_section` | Shows Top Priorities section with correct numbering and order |
| `test_tasks_objective_section` | Shows objective title as section heading with bulleted items |
| `test_tasks_urgency_section` | Groups ungrouped items by urgency label in correct order |

## Example Flow

```
User says: "show me my tasks" or "/tasks"
  |
  v
GPT calls: GET /tasks
  |
  v
API returns: pre-formatted markdown text (text/plain)
  |
  v
GPT displays: text verbatim (cannot reformat plain text)
  |
  v
User sees: organized sections with headings, not a flat list
```

## Related

- **PR:** [#11](https://github.com/btimmeny/signal-os/pull/11)
- **Predecessor:** Feature 010 (Dashboard GPT Training Fix)
- **Depends on:** Feature 009 (Task Dashboard) — uses `get_dashboard()` function
