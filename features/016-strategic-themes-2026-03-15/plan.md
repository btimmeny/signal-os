# Feature 016: Strategic Themes — Implementation Plan

## Step 1: Introduce Strategic Themes

1. Add `ThemeStatus` enum to `app/models.py` with values: ACTIVE, COMPLETED,
   DEFERRED, CANCELLED.
2. Add `StrategicTheme` ORM model with: id (UUID PK), title (String 512,
   indexed), description (Text, nullable), status (ThemeStatus), created_at,
   updated_at, initiatives (relationship).
3. Add Pydantic schemas to `app/schemas.py`: `ThemeCreateRequest`,
   `ThemeUpdateRequest`, `ThemeResponse`, `ThemeSeedRequest`.

## Step 2: Link Initiatives to Themes

4. Add `theme_id` FK column to `Initiative` model (Uuid, nullable,
   ForeignKey to strategic_themes.id, ondelete=SET NULL, indexed).
5. Add `theme` relationship on `Initiative` back to `StrategicTheme`.
6. Create Alembic migration `011_add_strategic_themes.py`.
7. Update `InitiativeCreateRequest` and `InitiativeUpdateRequest` to accept
   optional `theme_id`.
8. Update `InitiativeResponse` to include `theme_id` and `theme_title`.

## Step 3: Theme Service and Endpoints

9. Create `app/services/strategic_themes.py` with CRUD and seed functions.
10. Add 5 theme endpoints to `app/main.py`:
    - POST /themes/create
    - POST /themes/update
    - GET /themes/list
    - GET /themes/get
    - POST /themes/seed
11. Update `create_initiative()` to accept and store `theme_id`.
12. Update `update_initiative()` to convert `theme_id` string to UUID.

## Step 4: Update Reporting and Automation

13. Rewrite `format_dashboard_text()` to group by Theme > Initiative > Task.
14. Add `get_initiative_task_count()` to initiatives service.
15. Add initiative focus warning (>15 tasks) to `/initiatives/link` endpoint.

## Step 5: OpenAPI and Documentation

16. Update `openapi-gpt.yaml` with theme schemas and endpoint paths.
17. Create feature folder `016-strategic-themes-2026-03-15/` with spec,
    plan, and task docs.
18. Update `specification.md` feature index.

## Step 6: Testing

19. Write tests for theme CRUD, seeding, initiative linking, focus warning,
    and task rendering with theme hierarchy.
20. Run full test suite and verify all tests pass (83 existing + new).
21. Commit, push, and create PR.
