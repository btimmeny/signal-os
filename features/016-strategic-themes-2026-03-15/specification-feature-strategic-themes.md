# Feature 016: Strategic Themes

**Date:** 2026-03-15

## Motivation

Signal OS needed a top-level organizational hierarchy above initiatives.
Strategic Themes represent 6–12 month capability-level goals that group
related initiatives. The three-level hierarchy is:

**Strategic Theme → Initiative → Task (Commitment)**

This enables weekly reporting at the theme level, ensures every task maps to
a strategic pillar, and provides focus warnings when initiatives become
overloaded.

## Changes

### `app/models.py`

- Added `ThemeStatus` enum: `ACTIVE`, `COMPLETED`, `DEFERRED`, `CANCELLED`.
- Added `StrategicTheme` ORM model with `id`, `title`, `description`,
  `status`, `created_at`, `updated_at`, and `initiatives` relationship.
- Added `theme_id` FK column to `Initiative` (nullable, `ondelete=SET NULL`).
- Added `theme` relationship on `Initiative` back to `StrategicTheme`.

### `alembic/versions/011_add_strategic_themes.py`

New migration:
- Creates `strategic_themes` table.
- Adds `theme_id` column to `initiatives` table with FK constraint.

### `app/schemas.py`

- `ThemeCreateRequest`: title (required), description, status (default ACTIVE).
- `ThemeUpdateRequest`: theme_id (required), title/description/status optional.
- `ThemeResponse`: full theme fields with `from_orm_row()`.
- `ThemeSeedRequest`: list of `{title, description}` dicts.
- Updated `InitiativeCreateRequest` and `InitiativeUpdateRequest` to accept
  optional `theme_id`.
- Updated `InitiativeResponse` to include `theme_id` and `theme_title`.

### `app/services/strategic_themes.py` (new)

CRUD service with: `create_theme()`, `update_theme()`, `list_themes()`,
`get_theme()`, `seed_themes()`.

`seed_themes()` uses case-insensitive title matching for idempotency.

### `app/services/initiatives.py`

- `create_initiative()` accepts optional `theme_id`.
- `update_initiative()` converts `theme_id` string to UUID before setting.
- Added `get_initiative_task_count()` to count open linked commitments.

### `app/services/commitments.py` — `format_dashboard_text()`

Rewrote the rendering to group by theme:

```
Priority Execution
1. Task (person, date)

[Theme Name]
  [Initiative Name]
    * linked task (person, date)

Other Initiatives
  [Initiative Name]
    * linked task (person, date)

Everything Else
* unlinked task (person, date)
```

### `app/main.py`

Five new theme endpoints:
- `POST /themes/create` — Create a strategic theme
- `POST /themes/update` — Update a theme
- `GET /themes/list` — List themes (optional status filter)
- `GET /themes/get` — Get a single theme by ID
- `POST /themes/seed` — Idempotent seed of themes

Updated `POST /initiatives/link` to return a `warning` field when an
initiative has >15 active linked tasks (Automation Rule 3).

### `openapi-gpt.yaml`

- Added `ThemeCreateRequest`, `ThemeUpdateRequest`, `Theme`,
  `ThemeSeedRequest` schemas.
- Added 5 theme endpoint paths.
- Updated `Initiative`, `InitiativeCreateRequest`, `InitiativeUpdateRequest`
  schemas with `theme_id` / `theme_title` fields.

### Tests

15 new tests in `tests/test_strategic_themes.py`:
- Theme CRUD: create, list, list by status, update, update not found,
  get, get not found
- Seed: idempotent seeding
- Initiative-theme linking: create with theme, create without, update theme
- Focus warning: >15 tasks triggers warning
- Task rendering: theme grouping, unthemed initiatives, multiple themes

## Four Strategic Themes (to seed)

1. **AI-Native SDLC** — Transform software development into AI-assisted process
2. **Agent Infrastructure** — Build runtime systems for enterprise AI agents
3. **Knowledge Platform** — Enable AI systems to access firm knowledge
4. **Ecosystem and Organization** — Develop partnerships, governance, team org

## Automation Rules

1. Tasks inherit theme from their initiative via FK relationship
2. Tasks should belong to initiatives (GPT instructions guide this)
3. Initiative focus warning if >15 active linked tasks

## Migration

`011_add_strategic_themes.py` — Creates `strategic_themes` table and adds
`theme_id` FK to `initiatives`.

## Tests

All 98 tests pass (83 existing + 15 new).
