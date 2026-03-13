# Plan: Initiative-Grouped Rendering

## Objective

Replace flat "Initiative:" title-prefix rendering with join-table-based grouping: initiatives as headers with linked tasks indented beneath. Add `/initiatives/seed` endpoint for bulk-creating the 10 predefined initiatives.

## Prerequisites

- Access to the Signal OS repository
- Feature 014 (Initiatives) already merged

## Steps

### 1. Rewrite Initiatives Section Rendering

1. Open `app/services/commitments.py`
2. Update `format_dashboard_text()` Initiatives section:
   - Query all ACTIVE `Initiative` records
   - For each, query `InitiativeCommitmentLink` for linked open commitments
   - Render each initiative as a header with linked tasks indented beneath (`  * task`)
   - Omit initiatives with no linked open tasks

### 2. Implement Seed Service

1. Open `app/services/initiatives.py`
2. Add `seed_initiatives(db, titles)` function
3. For each title, check if initiative already exists (case-insensitive)
4. Create only new ones; return list of newly created initiatives

### 3. Add Seed Schema

1. Open `app/schemas.py`
2. Add `InitiativeSeedRequest` with `titles: List[str]`

### 4. Add Seed Endpoint

1. Open `app/main.py`
2. Add `POST /initiatives/seed` route calling `seed_initiatives()`

### 5. Update OpenAPI Spec

1. Open `openapi-gpt.yaml`
2. Add `InitiativeSeedRequest` schema
3. Add `POST /initiatives/seed` endpoint

### 6. Update Tests

1. Update `test_tasks_initiatives_section` to use initiative linking instead of title prefix
2. Update `test_tasks_three_section_order` to use initiative linking
3. Add `test_seed_initiatives` for seed endpoint

### 7. Verify and Submit

1. Run `pytest -v` — all tests must pass
2. Commit, push, create PR
