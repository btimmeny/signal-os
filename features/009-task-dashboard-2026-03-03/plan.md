# Plan: Task Dashboard

## Objective

Add a single `GET /commitments/dashboard` endpoint that returns all non-CLOSED commitments organized into three sections: Priority Ranked, By Objective, and Ungrouped (by urgency). Include GPT anti-hallucination training in the OpenAPI spec.

## Prerequisites

- Access to the Signal OS repository
- Features 001-008 already merged (urgency, priorities, objectives, linking)

## Steps

### 1. Implement Dashboard Service

1. Open `app/services/commitments.py`
2. Add `get_dashboard(db)` function that:
   - Fetches all non-CLOSED commitments
   - Separates items with `priority_order` (sorted ascending) into `priority_ranked`
   - Queries `ObjectiveCommitmentLink` for remaining items to group by objective
   - Groups unlinked items by urgency level in priority order
   - Returns dict with `total_open`, `priority_ranked`, `by_objective`, `ungrouped`

### 2. Add API Endpoint

1. Open `app/main.py`
2. Add `GET /commitments/dashboard` route
3. Serialize response using `CommitmentResponse.from_orm_with_days()`

### 3. Add GPT Anti-Hallucination Training

1. Open `openapi.yaml`
2. Add mandatory instruction block to top-level API description:
   - Call `GET /commitments/dashboard` when users ask about tasks
   - Include output template showing grouped section format
   - State explicitly that flat numbered list is WRONG
3. Add endpoint-level description with formatting rules
4. Add redirect warnings on `/commitments/open` and `/commitments/priorities`

### 4. Update Documentation

1. Update `specification.md` — FR-34, FR-35, endpoint entry
2. Update `architecture.md` — service function
3. Update `graph.md` — API route map

### 5. Write Tests

Add 6 tests:
1. `test_dashboard_empty` — Empty sections with no commitments
2. `test_dashboard_priority_ranked_first` — Priority items sorted correctly
3. `test_dashboard_grouped_by_objective` — Items grouped under objective
4. `test_dashboard_ungrouped_by_urgency` — Unlinked items grouped by urgency
5. `test_dashboard_closed_items_excluded` — CLOSED excluded
6. `test_dashboard_no_duplicates` — Multi-linked items appear once

### 6. Verify and Submit

1. Run `pytest -v` — all tests must pass
2. Commit, push, create PR
