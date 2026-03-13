# Plan: Task Detail Rendering

## Objective

Enhance the `/tasks` output to include all relevant detail fields (person, org, urgency, status, due date, channel, description) as sub-bullets under each task title.

## Prerequisites

- Access to the Signal OS repository
- Feature 011 (Tasks Plain Text Endpoint) already merged

## Steps

### 1. Add Detail Formatting Helper

1. Open `app/services/commitments.py`
2. Add `_format_task_details(c)` helper that builds detail lines for a commitment
3. Fields to render (when present): Person, Org, Urgency, Status, Due (Mon DD, YYYY), Channel (type + title), Note (description)

### 2. Update format_dashboard_text

1. Update `format_dashboard_text()` to render each task title in bold (`**title**`)
2. Include sub-bullet detail lines from `_format_task_details()` indented under each title

### 3. Update Tests

1. Update existing `/tasks` tests to match bold title format
2. Add `test_tasks_detail_fields` verifying all detail fields render correctly

### 4. Verify and Submit

1. Run `pytest -v` — all tests must pass
2. Commit, push, create PR
