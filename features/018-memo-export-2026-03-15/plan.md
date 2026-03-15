# Feature 018: Memo Export System -- Plan

## Implementation Steps

1. **Install python-docx** -- Add `python-docx==1.2.0` to requirements.txt (already done in Feature 017)
2. **Add export service functions** to `app/services/leadership_memos.py`:
   - `_parse_json_field()` -- helper to safely parse JSON text fields
   - `format_memo_markdown()` -- render memo as markdown with headings
   - `export_memo_md()` -- wrapper returning markdown string or None
   - `export_memo_docx()` -- wrapper returning docx bytes or None
3. **Add export endpoints** to `app/main.py`:
   - `GET /memos/export-md` -- returns `.md` file attachment
   - `GET /memos/export-docx` -- returns `.docx` file attachment
4. **Verify status transitions** -- confirm existing `/memos/update` supports bidirectional transitions (no code changes needed)
5. **Write tests** -- status transitions, markdown export, docx export, auth enforcement
6. **Update openapi-gpt.yaml** -- add 2 export operations, remove 2 lesser-used unlink operations to stay at 30 operationId limit
7. **Create feature documentation** -- specification, plan, task files

## Architecture Decisions

- Export functions are read-only and don't modify the database
- Word documents use Calibri 11pt with proper heading hierarchy
- Markdown uses standard `#` heading syntax
- Both formats include all memo sections (objective, priorities, lead updates, focus, criteria)
- Removed `unlinkCommitmentFromObjective` and `unlinkCommitmentFromInitiative` from GPT schema to stay within 30-operation limit (endpoints still exist in API, just not exposed to ChatGPT)
