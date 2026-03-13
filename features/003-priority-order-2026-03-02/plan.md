# Plan: Priority Ordering

## Objective

Add an explicit `priority_order` integer field to commitments so users can rank items independently of urgency categories (e.g. "this is number one on my list").

## Prerequisites

- Access to the Signal OS repository
- Features 001-002 (urgency levels) already merged

## Steps

### 1. Update the Data Model

1. Open `app/models.py`
2. Add `priority_order = Column(Integer, nullable=True)` to the `Commitment` model

### 2. Update Pydantic Schemas

1. Open `app/schemas.py`
2. Add `priority_order: Optional[int] = None` to `CommitmentOpenRequest`, `CommitmentUpdateRequest`, and `CommitmentResponse`
3. Create `CommitmentSetPriorityRequest` schema with `commitment_id: str` and `priority_order: int`

### 3. Create Database Migration

1. Create `alembic/versions/004_add_priority_order.py`
2. Add nullable `priority_order` integer column to `commitments` table
3. Downgrade drops the column

### 4. Implement Service Logic

1. Open `app/services/commitments.py`
2. Add `_reorder_priorities()` — shifts items at or above the target position up by 1
3. Add `_compact_priorities()` — removes gaps in priority numbering
4. Add `set_priority(db, commitment_id, priority_order)` — sets position and reorders
5. Add `list_priorities(db)` — returns all non-CLOSED commitments with priority_order, sorted ascending
6. Update `open_commitment()` and `update_commitment()` to handle `priority_order`

### 5. Add API Endpoints

1. Open `app/main.py`
2. Add `POST /commitments/set_priority` — calls `set_priority()` service
3. Add `GET /commitments/priorities` — calls `list_priorities()` service
4. Update `commitments_open` route to pass `priority_order`

### 6. Update OpenAPI Spec

1. Add `priority_order` field to relevant schemas
2. Add new endpoint definitions for `/commitments/set_priority` and `/commitments/priorities`

### 7. Update Documentation

1. Update `specification.md` — data model, FR-16, FR-17, endpoints
2. Update `architecture.md` — migration chain, service functions
3. Update `graph.md` — ER diagram, API route map

### 8. Write Tests

Add 5 tests:
1. `test_open_with_priority_order` — Create with `priority_order=1`
2. `test_set_priority` — Set priority via `/commitments/set_priority`
3. `test_priority_reordering` — Verify auto-shifting on insert
4. `test_list_priorities` — Verify sorted output
5. `test_update_priority_order` — Update via `/commitments/update`

### 9. Verify and Submit

1. Run `pytest -v` — all tests must pass
2. Commit, push, create PR
