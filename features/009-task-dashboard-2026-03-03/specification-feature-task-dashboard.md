# Task Dashboard

## Motivation

When users ask to see their task list, the AI agent needs a canonical, pre-organized endpoint to call. Without this, the agent might hallucinate tasks, forget items, or present an incomplete list. The dashboard endpoint provides a single source of truth that organizes all open commitments into a structured, presentation-ready format.

## Feature Summary

A new `GET /commitments/dashboard` endpoint that returns all non-CLOSED commitments organized into three sections:

1. **Priority Ranked** — Items with an explicit `priority_order`, sorted by rank (1 = top priority). These are always shown first.
2. **By Objective** — Remaining items grouped by their linked strategic objective. Each group includes the objective's title and status.
3. **Ungrouped** — Items with no priority and no linked objective, sub-grouped by urgency level (INCIDENT, NOW, SOON, SCHEDULED, SOMEDAY, ADMIN, UNSET).

Every non-CLOSED commitment appears exactly once across the three sections.

## GPT Training / Anti-Hallucination

The OpenAPI spec (`openapi.yaml`) includes explicit instructions at three levels:

1. **Top-level API description** — Mandatory instruction block that tells AI agents to call `GET /commitments/dashboard` when users ask about their tasks, includes an explicit output template showing the grouped section format, and explicitly states that a flat numbered list is WRONG.
2. **Endpoint-level description** — Detailed formatting rules with an example output format showing section headings (Top Priorities, objectives, urgency groups). Emphasizes NEVER flattening to a numbered list.
3. **Other list endpoints** (`/commitments/open`, `/commitments/priorities`) — Explicitly redirect AI agents to use `/commitments/dashboard` instead when showing the full task list.

Key anti-hallucination rules:
   - NEVER fabricate or recall tasks from memory
   - ALWAYS use the dashboard response as the single source of truth
   - Present EVERY item returned — NEVER omit or skip
   - NEVER flatten into a single numbered list — ALWAYS use grouped sections
   - Show `total_open` count for user verification

## Changes

### Service Layer
- **`app/services/commitments.py`** — Added `get_dashboard(db)` function that:
  - Fetches all non-CLOSED commitments
  - Separates items with `priority_order` (sorted ascending) from the rest
  - For remaining items, queries `ObjectiveCommitmentLink` to find objective associations
  - Groups linked items by their primary objective
  - Groups unlinked items by urgency level in priority order
  - Returns a dict with `total_open`, `priority_ranked`, `by_objective`, `ungrouped`

### Route
- **`app/main.py`** — Added `GET /commitments/dashboard` route that serializes the service response using `CommitmentResponse.from_orm_with_days()`

### OpenAPI Spec
- **`openapi.yaml`** — Added `/commitments/dashboard` path with full response schema and GPT training instructions in both the endpoint description and the top-level API description

### No Migration Required
This feature is read-only and queries existing tables (`commitments`, `objective_commitment_links`, `strategic_objectives`). No schema changes needed.

## API

### `GET /commitments/dashboard`

**Response:**
```json
{
  "total_open": 5,
  "priority_ranked": [
    { "id": "...", "title": "Top priority task", "priority_order": 1, ... },
    { "id": "...", "title": "Second priority", "priority_order": 2, ... }
  ],
  "by_objective": [
    {
      "objective_id": "...",
      "objective_title": "Increase Revenue",
      "objective_status": "ACTIVE",
      "commitments": [
        { "id": "...", "title": "Close Acme deal", ... }
      ]
    }
  ],
  "ungrouped": [
    {
      "group_label": "NOW",
      "commitments": [
        { "id": "...", "title": "Fix login bug", ... }
      ]
    },
    {
      "group_label": "SOMEDAY",
      "commitments": [
        { "id": "...", "title": "Refactor auth module", ... }
      ]
    }
  ]
}
```

## Tests Added

6 new tests in `tests/test_commitments.py`:

| Test | Description |
|------|-------------|
| `test_dashboard_empty` | Dashboard with no commitments returns empty sections |
| `test_dashboard_priority_ranked_first` | Items with priority_order sorted correctly in priority_ranked |
| `test_dashboard_grouped_by_objective` | Items linked to objectives grouped under objective title |
| `test_dashboard_ungrouped_by_urgency` | Unlinked items grouped by urgency in priority order |
| `test_dashboard_closed_items_excluded` | Closed commitments excluded from dashboard |
| `test_dashboard_no_duplicates` | Multi-linked items appear exactly once |

## Presentation Logic

```
User asks: "Show me my tasks"
  |
  v
AI Agent calls: GET /commitments/dashboard
  |
  v
Response arrives with organized sections
  |
  v
1. Show "Top Priorities" (priority_ranked, by rank number)
2. Show objectives as section headers (by_objective)
3. Show remaining items by urgency (ungrouped)
4. State total_open count for completeness verification
```
