# Feature 017: Weekly Platform Alignment Memo — Tasks

## Task List

- [x] Add `MemoStatus` enum to `app/models.py`
- [x] Add `PlatformLead` model to `app/models.py`
- [x] Add `LeadershipMemo` model to `app/models.py`
- [x] Create Alembic migration `012_add_platform_leads_and_memos.py`
- [x] Add Pydantic schemas for platform leads (create, update, response, seed)
- [x] Add Pydantic schemas for memos (create, update, response, status enum)
- [x] Create `app/services/platform_leads.py` with CRUD + seed
- [x] Create `app/services/leadership_memos.py` with CRUD + generation + rendering
- [x] Add 9 API endpoints to `app/main.py` (4 lead, 5 memo)
- [x] Update `tests/conftest.py` to import new models
- [x] Write 25 tests in `tests/test_weekly_memo.py`
- [x] Create feature folder 017 with specification, plan, task docs
- [x] Update `specification.md` with feature 017
- [x] Update `openapi-gpt.yaml` (stay within 30-op limit)
- [x] Run all tests (123 passed)
- [x] Commit, push, create PR
