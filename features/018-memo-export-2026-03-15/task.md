# Feature 018: Memo Export System -- Tasks

## Completed

- [x] Add `_parse_json_field()` helper to `app/services/leadership_memos.py`
- [x] Add `format_memo_markdown()` function to render memo as markdown
- [x] Add `export_memo_md()` wrapper function
- [x] Add `export_memo_docx()` function using python-docx
- [x] Add `GET /memos/export-md` endpoint to `app/main.py`
- [x] Add `GET /memos/export-docx` endpoint to `app/main.py`
- [x] Verify bidirectional status transitions work (no changes needed)
- [x] Add 17 new tests to `tests/test_weekly_memo.py`:
  - Status transitions: draft->finalized, finalized->draft, finalized->sent, sent->draft, full lifecycle
  - Markdown export: content, leads, not found, content-disposition
  - Docx export: validity, content-disposition, not found, content verification
  - Export after finalization
  - Auth enforcement on export endpoints
- [x] Update `openapi-gpt.yaml` with export operations (swapped out 2 unlink ops)
- [x] Create feature 018 documentation folder

## Files Changed

| File | Change |
|------|--------|
| `app/services/leadership_memos.py` | Added 4 export functions |
| `app/main.py` | Added 2 GET endpoints |
| `tests/test_weekly_memo.py` | Added 17 tests |
| `openapi-gpt.yaml` | Added 2 export ops, removed 2 unlink ops (stays at 30) |
| `requirements.txt` | python-docx already present from Feature 017 |
| `specification.md` | Added Feature 018 reference |
