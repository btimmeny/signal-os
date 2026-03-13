# Tasks: Status Reporting

## Task 1: Create ReportPeriod Enum and StatusReport Model
- **File:** `app/models.py`
- **Action:** Add `ReportPeriod` enum (WEEKLY, MONTHLY, QUARTERLY, ANNUAL) and `StatusReport` model
- **Acceptance:** Model has id, period_type, period_start, period_end, body, created_at

## Task 2: Create Pydantic Schemas
- **File:** `app/schemas.py`
- **Action:** Add `StatusReportCreateRequest`, `StatusReportResponse`, `StatusDataRequest`
- **Acceptance:** Create requires all fields; data request requires period_start and period_end

## Task 3: Create Alembic Migration
- **File:** `alembic/versions/009_add_status_reports.py`
- **Action:** Create `report_period` enum and `status_reports` table
- **Acceptance:** Migration runs cleanly up and down

## Task 4: Implement Report Storage Service
- **File:** `app/services/status_reports.py` (new)
- **Action:** Add `create_report()`, `list_reports()`, `get_report()`
- **Acceptance:** CRUD operations work correctly; filter by period_type returns expected results

## Task 5: Implement Data Gathering
- **File:** `app/services/status_reports.py`
- **Action:** Add `gather_status_data()` that aggregates objectives, linked commitments with period comments, objective updates, and commitment activity
- **Acceptance:** Returns structured payload with all related data for the specified period

## Task 6: Add API Endpoints
- **File:** `app/main.py`
- **Action:** Add `POST /status/report`, `GET /status/report`, `GET /status/reports`, `POST /status/data`
- **Acceptance:** All endpoints respond correctly with proper status codes

## Task 7: Update OpenAPI Spec and Documentation
- **Files:** `openapi.yaml`, `specification.md`, `architecture.md`, `graph.md`
- **Action:** Add schemas, endpoints, entity docs, migration chain
- **Acceptance:** All specs and docs reflect the new feature

## Task 8: Write Tests
- **File:** `tests/test_objectives.py`
- **Action:** Add 5 tests for create, list, get, full data gathering, and empty period
- **Acceptance:** All 5 new tests pass; all existing tests still pass

## Task 9: Verify and Submit
- **Action:** Run `pytest -v`, commit, push, create PR
- **Acceptance:** All tests pass, PR created
