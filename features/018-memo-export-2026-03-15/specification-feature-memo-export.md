# Feature 018: Memo Export System

## Overview

Allows users to export weekly leadership alignment memos to Word (.docx) and Markdown (.md) file formats. Supports iterating on memo status back and forth (DRAFT, FINALIZED, SENT) before committing to a final export.

## Problem

After generating and reviewing a memo, users need a way to distribute it outside the platform. The memo lifecycle should support going back and forth between statuses (not just one-way progression) so users can revise before exporting.

## Solution

1. **Bidirectional status transitions** -- the existing `/memos/update` endpoint already accepts any status value, so DRAFT <-> FINALIZED <-> SENT transitions work without code changes.
2. **Markdown export** (`GET /memos/export-md`) -- renders the memo as a structured markdown document with `#` headings, metadata block, and all sections.
3. **Word export** (`GET /memos/export-docx`) -- renders the memo as a `.docx` Word document using python-docx with Calibri 11pt font, centered title, heading levels, and bullet lists.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/memos/export-md?memo_id=X` | Download memo as `.md` file |
| GET | `/memos/export-docx?memo_id=X` | Download memo as `.docx` file |

Both endpoints return file attachments with appropriate MIME types and `Content-Disposition` headers.

## Memo Sections Exported

- Title: "AI Platform Weekly Leadership Memo"
- Metadata: To, From, Date, Status
- Strategic Objective
- Current Priorities (bulleted)
- Platform Updates (grouped by lead role)
- Focus for Next Week (bulleted)
- Success Criteria (bulleted)

## Dependencies

- `python-docx==1.2.0` (already in requirements.txt)

## Tests

- Status transition tests (DRAFT -> FINALIZED -> SENT and back)
- Full lifecycle test (DRAFT -> FINALIZED -> DRAFT -> FINALIZED -> SENT)
- Markdown export content and header verification
- Word export validity (PK zip header) and content verification
- 404 handling for missing memos
- Auth enforcement on export endpoints
