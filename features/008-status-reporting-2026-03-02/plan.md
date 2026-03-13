# Plan: Status Reporting

## Objective

Add status report creation, storage, and aggregated data gathering for weekly/monthly/quarterly/annual reporting periods.

## Prerequisites

- Access to the Signal OS repository
- Features 005-007 (objectives, linking, updates) already merged

## Steps

### 1. Create the ORM Model

1. Open `app/models.py`
2. Add `ReportPeriod` enum: WEEKLY, MONTHLY, QUARTERLY, ANNUAL
3. Add `StatusReport` model with: `id` (UUID PK), `period_type` (ReportPeriod), `period_start`, `period_end` (TIMESTAMPTZ), `body` (TEXT), `created_at`

### 2. Create Pydantic Schemas

1. Open `app/schemas.py`
2. Add `StatusReportCreateRequest` with `period_type`, `period_start`, `period_end`, `body`
3. Add `StatusReportResponse` with all fields
4. Add `StatusDataRequest` with `period_start`, `period_end`

### 3. Create Database Migration

1. Create `alembic/versions/009_add_status_reports.py`
2. Create `report_period` enum type and `status_reports` table

### 4. Implement Service Layer

1. Create `app/services/status_reports.py`
2. Add `create_report()` — store a report
3. Add `list_reports()` — list with optional period_type filter
4. Add `get_report()` — single lookup
5. Add `gather_status_data()` — aggregate objectives, linked commitments with period comments, objective updates, and commitment activity for a date range

### 5. Add API Endpoints

1. Add `POST /status/report` — store report
2. Add `GET /status/report` — get by ID
3. Add `GET /status/reports` — list with filter
4. Add `POST /status/data` — gather aggregated data

### 6. Update OpenAPI Spec and Documentation

1. Update `openapi.yaml` with schemas and endpoints
2. Update `specification.md`, `architecture.md`, `graph.md`

### 7. Write Tests

Add 5 tests:
1. `test_create_status_report` — Create a weekly report
2. `test_list_status_reports` — List and filter by period type
3. `test_get_status_report` — Get by ID
4. `test_gather_status_data` — Full integration: objective + commitment + link + comment + update
5. `test_gather_status_data_empty_period` — Empty period returns empty lists

### 8. Verify and Submit

1. Run `pytest -v` — all tests must pass
2. Commit, push, create PR
