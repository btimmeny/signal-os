# Feature 016: Strategic Themes — Tasks

## Task 1: Add ThemeStatus Enum and StrategicTheme Model
- File: `app/models.py`
- Add ThemeStatus enum (ACTIVE, COMPLETED, DEFERRED, CANCELLED)
- Add StrategicTheme ORM model with all fields and relationships
- Add theme_id FK and theme relationship to Initiative model

## Task 2: Create Alembic Migration
- File: `alembic/versions/011_add_strategic_themes.py`
- Create strategic_themes table
- Add theme_id column to initiatives table with FK constraint

## Task 3: Add Pydantic Schemas
- File: `app/schemas.py`
- ThemeCreateRequest, ThemeUpdateRequest, ThemeResponse, ThemeSeedRequest
- Update InitiativeCreateRequest, InitiativeUpdateRequest, InitiativeResponse

## Task 4: Create Strategic Themes Service
- File: `app/services/strategic_themes.py`
- Implement create_theme, update_theme, list_themes, get_theme, seed_themes
- seed_themes uses case-insensitive matching for idempotency

## Task 5: Add Theme Endpoints
- File: `app/main.py`
- POST /themes/create, /themes/update, /themes/seed
- GET /themes/list, /themes/get

## Task 6: Update Initiative Service
- File: `app/services/initiatives.py`
- Accept theme_id in create_initiative
- Convert theme_id string to UUID in update_initiative
- Add get_initiative_task_count for focus warning

## Task 7: Update Task Rendering
- File: `app/services/commitments.py`
- Rewrite format_dashboard_text() for Theme > Initiative > Task grouping
- Handle "Other Initiatives" section for unthemed initiatives

## Task 8: Add Initiative Focus Warning
- File: `app/main.py`
- In /initiatives/link, check task count after linking
- Return warning field if >15 active tasks on initiative

## Task 9: Update OpenAPI Spec
- File: `openapi-gpt.yaml`
- Add Theme schemas and 5 endpoint paths
- Update Initiative schemas with theme_id/theme_title

## Task 10: Write Tests
- File: `tests/test_strategic_themes.py`
- Theme CRUD tests (create, list, update, get, seed)
- Initiative-theme linking tests
- Focus warning test (>15 tasks)
- Task rendering tests (theme grouping, unthemed, multiple themes)

## Task 11: Documentation
- Create feature folder 016-strategic-themes-2026-03-15
- Write specification, plan, and task docs
- Update specification.md feature index
