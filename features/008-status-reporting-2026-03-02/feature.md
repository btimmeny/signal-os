# Feature: Status Reporting

## Motivation

With strategic objectives, linked commitments, commitment comments, and objective updates all in place, Signal OS has all the raw data needed to produce status reports at different cadences: weekly, monthly, quarterly, and annual. This feature provides:

1. **Data gathering** -- Aggregates all relevant information for a time period into a structured payload that an AI agent can use to compose a status narrative
2. **Report storage** -- Persists the generated status report for future reference

The AI agent (ChatGPT) calls `/status/data` to get the raw material, composes a narrative, then calls `/status/report` to save it.

## Data Model

**Table: `status_reports`**

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, default uuid4 |
| `period_type` | ENUM (report_period) | NOT NULL, INDEX |
| `period_start` | TIMESTAMPTZ | NOT NULL |
| `period_end` | TIMESTAMPTZ | NOT NULL |
| `body` | TEXT | NOT NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL |

**Enum: `report_period`** -- WEEKLY, MONTHLY, QUARTERLY, ANNUAL

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/status/report` | Store a status report |
| GET | `/status/report` | Get a single report by ID |
| GET | `/status/reports` | List reports (optional period_type filter) |
| POST | `/status/data` | Gather aggregated status data for a period |

## Status Data Gathering

The `/status/data` endpoint returns a structured payload:

```json
{
  "period_start": "2026-02-23T00:00:00Z",
  "period_end": "2026-03-01T23:59:59Z",
  "objectives": [
    {
      "objective_id": "...",
      "title": "Increase revenue by 20%",
      "status": "ACTIVE",
      "linked_commitments": [
        {
          "commitment_id": "...",
          "title": "Close deal with Acme",
          "status": "OPEN",
          "period_comments": [
            {"body": "Had follow-up call", "author": null, "created_at": "..."}
          ]
        }
      ],
      "period_updates": [
        {"body": "Pipeline is strong", "author": "Brian", "created_at": "..."}
      ]
    }
  ],
  "commitments_opened": [...],
  "commitments_closed": [...]
}
```

This gives the AI everything it needs to write a weekly status, monthly summary, quarterly review, or annual evaluation.

## Service Layer

**File:** `app/services/status_reports.py`

- `create_report(db, *, period_type, period_start, period_end, body)` -- Store a report
- `list_reports(db, *, period_type)` -- List with optional filter
- `get_report(db, *, report_id)` -- Single lookup
- `gather_status_data(db, *, period_start, period_end)` -- Aggregate all data for a period

## Migration

**File:** `alembic/versions/009_add_status_reports.py`

Creates the `status_reports` table and `report_period` enum type.

## Tests

- `test_create_status_report` -- Create a weekly report
- `test_list_status_reports` -- List all and filter by period type
- `test_get_status_report` -- Get by ID
- `test_gather_status_data` -- Full integration test: create objective, commitment, link, comment, update, then verify gathered data
- `test_gather_status_data_empty_period` -- Empty period returns empty lists

## Design Decisions

- **Two-step report generation:** The system gathers data (structured) and stores reports (text) separately, allowing the AI agent to compose the narrative
- **Period type is metadata:** The period_type on `/status/data` is informational -- the actual filtering is done by `period_start` and `period_end` timestamps
- **Reports are immutable:** Once created, reports are not updated -- create a new one if the narrative changes
- **Comprehensive aggregation:** `gather_status_data` pulls objectives, their linked commitments with period comments, objective updates, and commitment activity (opened/closed) all in one call
