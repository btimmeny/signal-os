# Feature 013 — Task List Categories

**Date:** 2026-03-03
**PR:** #18

## Motivation

The user provided a reference document specifying exactly how the task list
should be categorized and formatted when returned by the GPT. Instead of the
previous grouping (Top Priorities → By Objective → By Urgency), tasks should
be sorted into six named categories with emoji headers, matching the user's
preferred visual format.

## Categories (in display order)

| # | Header | Emoji | Rule |
|---|--------|-------|------|
| 1 | Ranked Execution | 🎯 | Has `priority_order` set |
| 2 | Immediate | 🔥 | Urgency is INCIDENT or NOW |
| 3 | Time-Bound / Compliance | 📅 | Has `due_at` set |
| 4 | Strategy | 🧠 | Linked to a strategic objective |
| 5 | Human Resources | 👥 | Has `person` field set |
| 6 | Administration | 🤝 | Everything else |

Each task appears in **exactly one** category (first match wins in the order
above). Empty categories are omitted.

## Formatting

- **Ranked Execution** items use keycap number emoji (1️⃣, 2️⃣, 3️⃣, …)
- All other items use bullet points (•)
- Due dates shown inline as "— Due Mon DD"
- No sub-detail bullets (clean, compact format matching the reference PDF)

## Example Output

```
🎯 Ranked Execution
1️⃣ Prepare repository for Marco demo
2️⃣ Architecture & vTeam Plan, AI SDLC
3️⃣ AI/SDLC Quarterly Roadmap

🔥 Immediate
• Book flights to London for offsite

📅 Time-Bound / Compliance
• Add goals to HCM — Due Mar 11
• Submit Outside Investment Accounts — Due Mar 13

🧠 Strategy
• Build evergreen strategy (UMA vs Devin)
• Build strategic pillars (Evergreen + AI SDLC architecture)

👥 Human Resources
• Move Albert to Matteo or Mike's team
• Internal mobility options for Cristian Sorescu (Toronto)
• Meet Jonathan Perry & Daniel Marcu

🤝 Administration
• Begin new chat with Cognition and GS team
• Team Lead to send weekly status (GPT format)
• Read Cognition article from Piyush
• Review ARM Running Architecture with Jack & Ace
```

## Changes

### `app/services/commitments.py`

- Added `_KEYCAP_DIGITS` list and `_keycap(n)` helper for numbered emoji
- Added `_due_suffix(c)` helper for inline due date formatting
- Rewrote `format_dashboard_text()` to categorize tasks into six buckets
  using the priority waterfall (first match wins)
- Removed `_format_task_details()` (sub-detail bullets replaced by clean
  compact format)

### `tests/test_commitments.py`

- Replaced 4 old `/tasks` tests with 7 new tests covering each category
  and the overall category ordering
- Total: 70 tests (67 → 70, net +3)

## Migration

None — formatting-only change in the `/tasks` response.
