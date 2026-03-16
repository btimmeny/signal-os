# Feature 019: Dynamic Memo System -- Tasks

## Completed

- [x] Add `email` column to `PlatformLead` model (nullable String(512))
- [x] Create migration `013_add_lead_email.py`
- [x] Update `PlatformLeadCreateRequest`, `PlatformLeadUpdateRequest`, `PlatformLeadResponse` schemas for email
- [x] Update `platform_leads.py` service to handle email field
- [x] Rewrite `leadership_memos.py` with five narrative paragraph builders
- [x] Rewrite `format_memo_markdown()` for narrative sections (no bullets)
- [x] Add file persistence: `save_memo_to_file()`, `_memo_filename()`, `_docx_filename()`
- [x] Add Pandoc conversion: `convert_memo_to_docx()` with 30s timeout
- [x] Add Gmail integration: `_build_recipient_list()`, `send_memo_email()`
- [x] Add workflow orchestration: `execute_memo_workflow()`
- [x] Update `get_or_generate_memo_text()` to use full workflow
- [x] Update `MemoResponse` schema: `focus_next_week` and `success_criteria` changed from list to string
- [x] Update existing tests for new narrative format
- [x] Add new tests for narrative format, file persistence, Pandoc, Gmail, workflow
- [x] Create feature 019 documentation folder
- [x] Update `specification.md` with Feature 019 reference

## Files Changed

| File | Change |
|------|--------|
| `app/models.py` | Added `email` column to `PlatformLead` |
| `app/schemas.py` | Updated `MemoResponse` for narrative text fields, added `_parse_text_or_json` |
| `app/services/leadership_memos.py` | Complete rewrite: narrative builders, file persistence, Pandoc, Gmail, workflow |
| `app/services/platform_leads.py` | Handle email field in create/update/seed |
| `alembic/versions/013_add_lead_email.py` | Migration for email column |
| `tests/test_weekly_memo.py` | Updated assertions + new workflow tests |
| `specification.md` | Added Feature 019 reference |
