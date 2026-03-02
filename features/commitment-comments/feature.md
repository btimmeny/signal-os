# Feature: Commitment Comments

## Overview

Adds the ability to attach timestamped comments to commitments. Comments serve as a running log of updates, meeting notes, progress reports, and context related to each action item. This creates a history trail that can be queried later to answer questions like "tell me what happened with X."

## Motivation

Users need to track not just the status of a commitment, but the evolving context around it. For example:
- "I had a meeting about this and here's where we stand"
- "Waiting on legal review, spoke to Jane on Monday"
- "Partial progress — completed the first two items"

This history will be used by future features (e.g., status summaries, AI-generated recaps) to provide richer context about each commitment.

## Data Model

A new `commitment_comments` table (separate from `commitments`) with a foreign key reference:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Auto-generated | Unique identifier |
| `commitment_id` | UUID (FK) | Yes | References `commitments.id` with `ON DELETE CASCADE` |
| `body` | Text | Yes | The comment content (min 1 character) |
| `author` | String (256) | No | Who wrote the comment |
| `created_at` | Timestamp | Yes (auto) | When the comment was created |

Comments are cascade-deleted when the parent commitment is deleted.

## API Endpoints

### POST /commitments/comment

Add a comment to a commitment.

**Request:**
```json
{
  "commitment_id": "uuid-string",
  "body": "Had a meeting about this — decided to move forward with option B",
  "author": "Alice"
}
```

**Response:** `200` with the created comment object, or `404` if the commitment doesn't exist.

### GET /commitments/comments?commitment_id=uuid-string

List all comments for a commitment, ordered oldest to newest.

**Response:** `200` with array of comment objects, or `404` if the commitment doesn't exist. Returns an empty array if the commitment exists but has no comments.

## Changes

### New Files
- `app/services/comments.py` — Service layer with `add_comment()` and `list_comments()` functions
- `alembic/versions/005_add_commitment_comments.py` — Migration to create `commitment_comments` table
- `features/commitment-comments/feature.md` — This document

### Modified Files
- `app/models.py` — Added `CommitmentComment` ORM model and `Commitment.comments` relationship
- `app/schemas.py` — Added `CommentCreateRequest` and `CommentResponse` Pydantic schemas
- `app/main.py` — Added `POST /commitments/comment` and `GET /commitments/comments` routes
- `openapi.yaml` — Added `CommentCreateRequest`, `Comment` schemas, and both endpoints
- `specification.md` — Added Comment entity (4.3), FR-18, FR-19, and endpoint table entries
- `architecture.md` — Updated project structure, service layer, data layer, schema, and migration chain
- `graph.md` — Updated ER diagram, API route map, and module dependency graph
- `tests/conftest.py` — Registered `CommitmentComment` model for test DB creation
- `tests/test_commitments.py` — Added 7 new tests

## Migration

**Revision:** `005` (depends on `004`)

Creates the `commitment_comments` table with columns: `id` (UUID PK), `commitment_id` (UUID FK with CASCADE), `body` (TEXT NOT NULL), `author` (VARCHAR(256) NULLABLE), `created_at` (TIMESTAMPTZ NOT NULL). Indexed on `commitment_id`.

## Tests Added

| Test | Description |
|------|-------------|
| `test_add_comment` | Add a comment with author and verify response fields |
| `test_list_comments` | Add multiple comments and verify ordering (oldest first) |
| `test_comment_on_nonexistent_commitment` | Returns 404 for non-existent commitment |
| `test_list_comments_nonexistent_commitment` | Returns 404 for non-existent commitment |
| `test_comment_empty_body_rejected` | Empty body returns 422 validation error |
| `test_comments_empty_for_new_commitment` | New commitment returns empty comment list |
| `test_comments_deleted_with_commitment` | Comments persist after closing (accessible for history) |

## Design Decisions

1. **Separate table:** Comments are stored in their own table (`commitment_comments`) rather than a JSON array on the commitment, enabling efficient querying, pagination in the future, and proper relational integrity.
2. **Select loading:** The `Commitment.comments` relationship uses `lazy="select"` (not joined) to avoid loading all comments on every commitment fetch — comments are only loaded when explicitly requested.
3. **Cascade delete:** Comments are automatically deleted when a commitment is deleted (via `ON DELETE CASCADE`), but closing a commitment preserves its comments for historical reference.
4. **Body validation:** The `body` field requires at least 1 character (`min_length=1`), preventing empty comments.
5. **Optional author:** The `author` field is optional to support both human-attributed and system-generated comments.
