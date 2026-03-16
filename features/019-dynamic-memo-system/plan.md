# Feature 019: Dynamic Memo System -- Plan

## Implementation Steps

1. **Add email field to PlatformLead** -- Add nullable `email` column to `platform_leads` table via migration 013. Update model, schemas, and service.
2. **Rewrite narrative generation** -- Replace bullet-list memo format with five narrative paragraph builders that dynamically query database:
   - `_build_narrative_strategic_objective()` -- pulls from active StrategicTheme or default
   - `_build_narrative_progress()` -- summarizes recent activity, attributes to leads
   - `_build_narrative_week_ahead()` -- highlights items due in next 7 days
   - `_build_narrative_ownership()` -- one sentence per active lead
   - `_build_narrative_success_criteria()` -- derives from active initiatives
3. **Rewrite format_memo_markdown()** -- Output new section order with `##` headings, narrative paragraphs, no bullets
4. **Add file persistence** -- Save `.md` files to `/leadership-memos/ai-platform/weekly/`
5. **Add Pandoc conversion** -- Convert `.md` to `.docx` via subprocess, save to `/exports/` subfolder
6. **Add Gmail integration** -- Send memo email to all active leads with `.docx` attachment via SMTP
7. **Add workflow orchestration** -- `execute_memo_workflow()` chains generate -> save -> convert -> email
8. **Update /memo endpoint** -- Trigger full workflow on `/memo` call (without email by default)
9. **Update MemoResponse schema** -- Change `focus_next_week` and `success_criteria` from list to string type for narrative text
10. **Write tests** -- Narrative format, file persistence, Pandoc, Gmail, workflow
11. **Create feature documentation** -- specification, plan, task files

## Architecture Decisions

- Narrative builders are separate functions for testability and maintainability
- File persistence uses `pathlib.Path` for cross-platform compatibility
- Pandoc conversion has 30-second timeout and graceful fallback to python-docx
- Gmail integration uses env vars (not hardcoded credentials) and is skipped if not configured
- `/memo` endpoint does not send email by default (only file persistence + conversion)
