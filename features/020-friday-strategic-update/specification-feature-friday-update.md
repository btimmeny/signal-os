# Feature 020: Friday Strategic Execution Update

## Overview

Automatically generates a Friday leadership execution update summarizing the most meaningful signals from the past week. Produces three strategic narrative options, a Strategy Confidence Score, week-over-week trend analysis, and a ready-to-forward email.

## Requirements

### Signal Extraction
- Query commitments, initiatives, themes, and comments from the past 7 days
- Identify closed tasks, newly opened tasks, overdue items, and upcoming deadlines
- Detect initiative movement (tasks closed per initiative) and stalled initiatives
- Capture priority-ranked tasks and active strategic themes

### Narrative Generation
- Generate exactly 3 narrative drafts with different strategic framings:
  1. **Execution Progress** — focuses on what got done and delivery velocity
  2. **Momentum** — focuses on trajectory, growth, and expanding capability
  3. **Alignment** — focuses on how execution connects to strategy
- Each narrative: ~150-200 words, 3 prose paragraphs (Week Summary, Execution Focus, Next Week)
- No bullet lists — prose paragraphs only
- Each framing includes: Strategic Objective, Why This Framing Works, Behavior It Drives
- Narratives must be data-driven (reference actual tasks, initiatives, themes from the system)

### Strategy Confidence Score
- Score range: 0-100
- Four weighted components:
  - Execution Progress (35%): task closure rate vs workload
  - Momentum Signals (25%): initiative movement, new work entering system
  - Alignment Signals (20%): priorities set, themes defined, initiatives connected
  - Friction Signals (20%, inverted): overdue tasks, stalled initiatives reduce score
- Includes trend direction (up/down/stable) compared to previous week
- Includes explanation text summarizing key score drivers

### Recommended Narrative Selection
- Algorithm selects the most appropriate framing based on current signals
- High closures -> Execution Progress
- Strong initiative movement -> Momentum
- Stalled initiatives -> Alignment (to address gaps)
- Includes reason for recommendation

### Strategic Narrative Continuity
- Explains how this week's execution contributes to the long-term mission
- References active strategic themes
- Compares to previous week's score when available

### Forwardable Version
- Clean, standalone version for Brian to forward to the team
- Contains only the recommended narrative + confidence score
- No internal framing options or scoring details

### Email Structure
1. Greeting to Brian
2. Narrative Option 1 (with strategic explanation)
3. Narrative Option 2 (with strategic explanation)
4. Narrative Option 3 (with strategic explanation)
5. Recommended Narrative (which one and why)
6. Strategic Narrative Continuity
7. Strategy Confidence Signal (score, trend, components, explanation)
8. Forwardable Version (ready to copy-paste and forward)

### Endpoints
- `POST /friday-update` — Generate a new Friday update (triggers email if configured)
- `GET /friday-update/latest` — Get the most recent update
- `GET /friday-update/list` — List recent updates

### Data Persistence
- `WeeklyStrategyUpdate` model stores all generated content
- Signal snapshot preserved as JSON for audit trail
- Previous update reference for trend comparison

## Technical Details

- **Database**: New `weekly_strategy_updates` table (migration 014)
- **Service**: `app/services/friday_update.py`
- **Email**: Gmail SMTP via `GMAIL_USER` and `GMAIL_APP_PASSWORD` env vars
- **Tests**: 38 tests covering signal extraction, scoring, narratives, email structure, endpoints, persistence
