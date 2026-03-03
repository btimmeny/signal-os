# Dashboard GPT Training Fix

## Motivation

After implementing the task dashboard (feature 009), GPT was still returning tasks as a flat numbered list (1-16) instead of using the grouped section format (Top Priorities, By Objective, By Urgency). The OpenAPI spec instructions were not strong enough to override GPT's default behavior of flattening JSON responses.

## Feature Summary

Strengthened the GPT training instructions in the OpenAPI spec to enforce the grouped dashboard format and explicitly prohibit flat numbered lists. Added redirect warnings on alternative list endpoints.

## Changes

### OpenAPI Spec (`openapi.yaml`)

1. **Top-level API description** — Added an explicit output template showing the exact grouped format GPT should use, with a clear statement that a flat numbered list is WRONG
2. **`/commitments/dashboard` endpoint description** — Added detailed formatting rules with an example output showing section headings (Top Priorities, objectives, urgency groups). Emphasized NEVER flattening to a numbered list
3. **`/commitments/open` endpoint** — Added redirect warning telling GPT to use `/commitments/dashboard` instead for task list display
4. **`/commitments/priorities` endpoint** — Added same redirect warning

### Route Docstring (`app/main.py`)

- Updated the `/commitments/dashboard` route docstring with the same grouped format example and anti-flat-list instruction

## No Code Changes

This feature only updated documentation and GPT instructions. No service logic, models, schemas, or migrations were changed.

## No New Tests

No functional changes — instruction-only update. All 62 existing tests continued to pass.

## Outcome

This fix was not sufficient on its own — GPT continued to flatten the JSON response into a numbered list despite the stronger instructions. This led to feature 011 (plain text `/tasks` endpoint) as the definitive solution.

## Related

- **PR:** [#10](https://github.com/btimmeny/signal-os/pull/10)
- **Predecessor:** Feature 009 (Task Dashboard)
- **Successor:** Feature 011 (Tasks Plain Text Endpoint)
