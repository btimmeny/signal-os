# Feature: Priority Ordering

## Summary

Adds an explicit `priority_order` integer field to commitments, allowing users to rank items independently of urgency categories. Users can say "this is number one on my list" or "place this as number five" and maintain a running overall priority list.

## Motivation

Urgency categories (INCIDENT, NOW, SOON, SCHEDULED, SOMEDAY, ADMIN) describe *when* something should be done, but they don't capture *relative importance* within or across categories. A user may have three NOW items but need to clearly rank which one comes first. Priority ordering solves this by providing an explicit numeric rank (1 = top priority) that is independent of urgency.

## Changes

### Modified Files

| File | Change |
|------|--------|
| `app/models.py` | Added `priority_order` nullable Integer column to `Commitment` |
| `app/schemas.py` | Added `priority_order` to `CommitmentOpenRequest`, `CommitmentUpdateRequest`, `CommitmentResponse`; added `CommitmentSetPriorityRequest` schema |
| `app/services/commitments.py` | Added `_reorder_priorities()`, `_compact_priorities()`, `set_priority()`, `list_priorities()` functions; updated `open_commitment()` and `update_commitment()` to handle `priority_order` |
| `app/main.py` | Added `POST /commitments/set_priority` and `GET /commitments/priorities` endpoints; updated `open_commitment` route to pass `priority_order` |
| `openapi.yaml` | Added `priority_order` field to schemas and new endpoint definitions |
| `specification.md` | Added `priority_order` field to data model table; added FR-16 and FR-17; added new endpoints to API surface |
| `architecture.md` | Added migration 004 to project structure and revision chain; added `set_priority()` and `list_priorities()` to service layer docs |
| `graph.md` | Added `priority_order` to ER diagram; added `/set_priority` and `/priorities` to API route map |

### New Files

| File | Description |
|------|-------------|
| `alembic/versions/004_add_priority_order.py` | Alembic migration adding nullable `priority_order` integer column to `commitments` table |
| `features/priority-order/feature.md` | This feature documentation |

## Database Migration

- **Migration:** `004_add_priority_order`
- **Revision chain:** `003` -> `004`
- **Change:** Adds `priority_order INTEGER NULLABLE` column to `commitments` table
- **Rollback:** Drops the `priority_order` column

## API Impact

### New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/commitments/set_priority` | Set a commitment's position in the priority list (auto-shifts other items) |
| GET | `/commitments/priorities` | List all non-CLOSED commitments with a priority_order, sorted by rank |

### Modified Endpoints

| Method | Path | Change |
|--------|------|--------|
| POST | `/commitments/open` | Accepts optional `priority_order` field |
| POST | `/commitments/update` | Accepts optional `priority_order` field |

### Reordering Behavior

When a commitment is placed at position N:
1. All non-CLOSED commitments with `priority_order >= N` are shifted up by 1
2. The target commitment is set to position N
3. Priorities are compacted to ensure contiguous numbering (1, 2, 3... no gaps)

## Tests Added

| Test | Description |
|------|-------------|
| `test_open_with_priority_order` | Create a commitment with `priority_order=1` |
| `test_set_priority` | Set priority on an existing commitment via `/commitments/set_priority` |
| `test_priority_reordering` | Verify auto-shifting when inserting at a position (e.g., insert at 2 shifts existing 2,3 to 3,4) |
| `test_list_priorities` | Verify `/commitments/priorities` returns only ranked items, sorted correctly |
| `test_update_priority_order` | Update `priority_order` via the existing `/commitments/update` endpoint |
