# Feature 012 — Task Detail Rendering

**Date:** 2026-03-03
**PR:** #17

## Motivation

The `/tasks` endpoint returned only task titles and due dates. Users need to see
all relevant details (person, organization, urgency, status, due date, channel,
description) inline so the GPT response is a comprehensive view without
requiring follow-up queries.

## Changes

### `app/services/commitments.py`

- Added `_format_task_details(c)` helper that builds detail lines for a single
  commitment. Fields rendered (when present):
  - **Person** — who the task involves
  - **Org** — organization context
  - **Urgency** — INCIDENT / NOW / SOON / SCHEDULED / SOMEDAY / ADMIN
  - **Status** — OPEN / WAITING / SNOOZED
  - **Due** — formatted as `Mon DD, YYYY`
  - **Channel** — channel type + optional title
  - **Note** — commitment description
- Updated `format_dashboard_text()` to render each task title in bold and
  include sub-bullet detail lines from `_format_task_details()`.

### `tests/test_commitments.py`

- Updated existing `/tasks` tests to match bold title format (`**title**`).
- Added `test_tasks_detail_fields` verifying all detail fields render correctly.

## Output Format Example

```
**16 open tasks**

## Top Priorities
1. **Review proposal**
   - Person: Jane Smith
   - Org: Acme Corp
   - Urgency: NOW
   - Status: OPEN
   - Due: Mar 15, 2026
   - Channel: meeting — Weekly sync
   - Note: Need to finalize Q2 plan

## Revenue Growth
- **Close big deal**
  - Person: Sales Team
  - Urgency: SOON

## ADMIN
- **Cleanup old records**
  - Status: OPEN
```

## Migration

None — read-only formatting change.

## API Impact

`GET /tasks` response now includes detail sub-bullets for each task. The
response is still plain text markdown, displayed verbatim by GPT.
