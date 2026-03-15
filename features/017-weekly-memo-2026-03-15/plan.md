# Feature 017: Weekly Platform Alignment Memo — Implementation Plan

## Steps

1. **Add models** — `PlatformLead` and `LeadershipMemo` to `app/models.py` with `MemoStatus` enum
2. **Create migration** — `012_add_platform_leads_and_memos.py` for both new tables
3. **Add schemas** — Pydantic request/response schemas in `app/schemas.py` for leads and memos
4. **Create platform_leads service** — CRUD + seed in `app/services/platform_leads.py`
5. **Create leadership_memos service** — CRUD + generation + rendering in `app/services/leadership_memos.py`
6. **Add endpoints** — 9 new routes in `app/main.py` (4 lead, 5 memo)
7. **Update conftest.py** — Register `PlatformLead` and `LeadershipMemo` models
8. **Write tests** — 25 tests in `tests/test_weekly_memo.py`
9. **Create feature folder** — specification, plan, task docs
10. **Update specification.md** — Add feature 017 to the index
11. **Update openapi-gpt.yaml** — Add `/memos/generate` endpoint (stay within 30-op limit)
12. **Run tests** — Verify all pass
13. **Commit, push, create PR**
