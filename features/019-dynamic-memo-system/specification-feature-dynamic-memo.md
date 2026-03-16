# Feature 019: Dynamic AI Platform Weekly Leadership Memo System

## Overview

Restructures the weekly leadership memo system to be fully dynamic, narrative-driven, file-persisted, and email-distributed. All leadership roles, ownership, and organizational references are resolved dynamically from database tables at runtime -- nothing is hardcoded.

## Problem

The existing memo system (Features 017-018) used bullet-list formatting and did not persist memos to the file system, convert to Word via Pandoc, or distribute via email. Leadership references were partially hardcoded rather than fully data-driven.

## Solution

1. **Narrative paragraphs** -- All memo sections are rendered as 3-5 sentence narrative paragraphs. No bullet lists. Target length: 350-500 words.
2. **Dynamic leadership resolution** -- All names, roles, and organizational structure are queried from the `platform_leads` table at generation time.
3. **Strict section order**:
   - Strategic Objective
   - Progress This Week
   - Week Ahead
   - Ownership & Execution
   - Success Criteria
4. **File persistence** -- Memos are saved as Markdown to `/leadership-memos/ai-platform/weekly/` in the repository.
5. **Pandoc conversion** -- Markdown files are converted to Word (.docx) via Pandoc subprocess and saved to `/leadership-memos/ai-platform/weekly/exports/`.
6. **Gmail distribution** -- Memos are emailed to all active platform leads via Gmail SMTP using `GMAIL_USER` and `GMAIL_APP_PASSWORD` environment variables.
7. **Full workflow** -- The `/memo` endpoint triggers the complete pipeline: generate -> save -> convert (email only on explicit request).

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/memo` | Trigger full workflow (generate, save, convert) and return formatted text |
| POST | `/memos/generate` | Generate a new memo for the current week |
| GET | `/memos/export-md?memo_id=X` | Download memo as `.md` file |
| GET | `/memos/export-docx?memo_id=X` | Download memo as `.docx` file |

## Database Changes

- Added `email` column (nullable String(512)) to `platform_leads` table via migration 013.

## Narrative Builders

| Function | Section | Data Source |
|----------|---------|-------------|
| `_build_narrative_strategic_objective()` | Strategic Objective | Active `StrategicTheme` or default |
| `_build_narrative_progress()` | Progress This Week | Active initiatives + commitments + leads |
| `_build_narrative_week_ahead()` | Week Ahead | Commitments due in next 7 days |
| `_build_narrative_ownership()` | Ownership & Execution | Active platform leads |
| `_build_narrative_success_criteria()` | Success Criteria | Active initiatives + high-priority commitments |

## File Persistence

- Markdown: `/leadership-memos/ai-platform/weekly/ai-platform-weekly-memo-YYYY-MM-DD.md`
- Word: `/leadership-memos/ai-platform/weekly/exports/ai-platform-weekly-memo-YYYY-MM-DD.docx`
- Idempotent: calling `/memo` twice in the same week updates rather than duplicates.

## Dependencies

- `python-docx==1.2.0` (existing)
- Pandoc (system-level, verified available)
- Gmail SMTP (env vars: `GMAIL_USER`, `GMAIL_APP_PASSWORD`)

## Tests

- Narrative format verification (no bullets, paragraph structure)
- File persistence (save and idempotency)
- Pandoc conversion (mocked subprocess)
- Gmail integration (mocked SMTP)
- Full workflow orchestration
- All 141+ existing tests pass with backward compatibility
