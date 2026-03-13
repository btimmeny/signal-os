# Plan: Task List Categories

## Objective

Reformat the `/tasks` output into six emoji-headed categories matching the user's preferred visual format, replacing the previous three-section grouping.

## Prerequisites

- Access to the Signal OS repository
- Features 011-012 (plain text endpoint, detail rendering) already merged

## Steps

### 1. Define Category Rules

Establish the six categories in display order (first match wins):

| # | Header | Emoji | Rule |
|---|--------|-------|------|
| 1 | Ranked Execution | :dart: | Has `priority_order` set |
| 2 | Immediate | :fire: | Urgency is INCIDENT or NOW |
| 3 | Time-Bound / Compliance | :calendar: | Has `due_at` set |
| 4 | Strategy | :brain: | Linked to a strategic objective |
| 5 | Human Resources | :busts_in_silhouette: | Has `person` field set |
| 6 | Administration | :handshake: | Everything else |

### 2. Add Keycap Emoji Helper

1. Open `app/services/commitments.py`
2. Add `_KEYCAP_DIGITS` list for numbered emoji (1-9)
3. Add `_keycap(n)` helper function

### 3. Add Due Date Suffix Helper

1. Add `_due_suffix(c)` helper for inline due date formatting ("-- Due Mon DD")

### 4. Rewrite format_dashboard_text

1. Replace the three-section rendering with six-category waterfall
2. Each task appears in exactly one category (first match wins)
3. Ranked Execution uses keycap emoji; all others use bullet points
4. Empty categories are omitted
5. Remove `_format_task_details()` (clean compact format replaces sub-details)

### 5. Update Tests

1. Replace existing `/tasks` tests with 7 new tests covering each category and ordering
2. Verify each category's emoji header and content rules

### 6. Verify and Submit

1. Run `pytest -v` -- all tests must pass
2. Commit, push, create PR
