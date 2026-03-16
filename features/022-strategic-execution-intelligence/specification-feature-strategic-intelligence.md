# Feature 022: Strategic Execution Intelligence System

## Purpose

Automatically convert task activity into strategic insight and produce scheduled weekly leadership updates with durable memory across sessions. All strategic commentary is persisted in dedicated tables so the system operates independently of any single session.

## Datastore Architecture

### New Tables

1. **strategic_contribution_notes** — Records the strategic contribution of each task when opened
   - note_id, task_id, initiative_id, strategic_theme, strategic_contribution_note, source, created_at

2. **execution_impact_notes** — Records the execution impact when a task is closed
   - impact_id, task_id, initiative_id, execution_impact_note, strategic_signal_flag, created_at

3. **strategic_narratives** — Week-over-week strategic understanding
   - date, strategic_objective, strategic_themes (JSON), momentum_signals (JSON), friction_signals (JSON), narrative_summary

4. **strategy_confidence_history** — Tracks confidence score trends over time
   - date, confidence_score, previous_score, trend_direction, confidence_explanation

5. **weekly_narratives** — Three narrative drafts per week with different framings
   - week_date, narrative_type, strategic_objective, narrative_text, recommended_flag

### Extended Tables

- **strategic_signals** — Added `confidence_weight` column (Integer, default 50)

## Task Event Processing

### On Task Open
- Determine strategic contribution by checking initiative and theme links
- Generate a StrategicContributionNote with inferred contribution text
- If no initiative/theme link exists, flag as unclear for Brian to clarify

### On Task Close
- Generate an ExecutionImpactNote describing the strategic impact
- Determine if the closure represents a strategic signal (high-signal flag)
- Use signal category classification from Feature 021

## Strategic Signal Extraction

- Analyze signals from past 7 days
- Identify high-signal progress (integrations, capabilities, AI SDLC, agent infrastructure, pilots, tooling)
- Ignore low-level operational tasks unless they unblock strategic work

## Weekly Friday Execution Update

### Pipeline Steps
1. **Query StrategicSignals** from past 7 days
2. **Update StrategicNarrative** record for the week
3. **Calculate Strategy Confidence Score** (40% execution, 25% momentum, 20% alignment, negative friction)
4. **Generate three narrative drafts** (Execution Progress, Momentum, Alignment) — 150-200 words each
5. **Explain why each narrative works**
6. **Select recommended narrative**

## Strategy Confidence Score

- **0-30**: Struggling — strategy execution not translating
- **30-60**: Mixed — some signals but gaps remain
- **60-80**: Strong — strategy clearly executing
- **80-100**: Clearly Working — strong signal across all dimensions

### Trend Direction
- **Improving**: Score increased ≥5 points from previous week
- **Flat**: Score changed <5 points
- **Declining**: Score decreased ≥5 points from previous week

## Email Output

- **Subject**: "AI Platform Weekly Status Draft — Strategic Update"
- **Recipient**: Brian
- **Sections**: Three narrative options, recommended narrative, strategic continuity analysis, confidence signal, forwardable version

## Scheduled Execution

- APScheduler configured for **Friday 12:00 PM UTC**
- Runs the full intelligence update pipeline automatically

## Idempotency Rules

- Task closures do not create duplicate signals (check before insert)
- WeeklyNarratives update existing weekly entries rather than creating duplicates
- Confidence scores only update when new signals exist
- All logic relies on datastore queries rather than session memory

## Session Independence

- System functions even if a new session starts
- All reasoning inputs loaded from datastore
- Workflow: retrieve data → analyze → generate narrative → store outputs

## SECTION 6 — Friday ChatGPT Review Session

Each Friday update creates a dedicated ChatGPT conversation session.

### Session Management
- **Session title**: "AI Platform Weekly Memo Review — YYYY-MM-DD"
- Only one session per week (idempotent — reuse if one already exists)
- Status transitions: open → finalized

### Session Initialization
Preload the conversation with:
- Strategic objective
- Weekly execution signals
- Strategy Confidence Score
- Three narrative drafts
- Narrative explanations
- Recommended narrative
- Strategic continuity analysis

### Opening Message
> Below are the three narrative drafts for this week's AI Platform leadership update along with the recommended option. Let's refine this together.

### New Tables

6. **weekly_review_sessions** — Tracks ChatGPT review sessions per week
   - id, week_date, session_title, chatgpt_session_link, status, created_at

## SECTION 7 — Strategy Debrief Conversation

At the beginning of each review session, the system initiates a structured Strategy Debrief.

### Default Debrief Questions
1. What progress this week most meaningfully advanced the platform objective?
2. Where do you believe we made less progress than expected?
3. Is there a signal that our strategy might need adjustment?
4. What should the team feel most momentum about right now?

### Debrief Storage
- Brian's responses stored in StrategyDebriefRecords (not session memory)
- Each record includes: question, response, derived_insight
- Idempotent per week — same question updates rather than duplicates

### New Tables

7. **strategy_debrief_records** — Stores debrief Q&A per week
   - id, week_date, question, response, derived_insight, recorded_at

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /intelligence/generate | Trigger full intelligence update |
| GET | /intelligence/contribution-notes | List recent contribution notes |
| GET | /intelligence/impact-notes | List recent impact notes |
| GET | /intelligence/unclear-contributions | Get notes needing clarification |
| PATCH | /intelligence/contribution-notes/{id} | Confirm/update a note |
| GET | /intelligence/narratives | List strategic narratives |
| GET | /intelligence/confidence-history | Get confidence score history |
| GET | /intelligence/confidence-latest | Get most recent score |
| GET | /intelligence/weekly-narratives | Get current week's 3 narrative drafts |
| GET | /intelligence/recommended-narrative | Get recommended narrative |
| POST | /intelligence/review-sessions | Create/get review session for this week |
| GET | /intelligence/review-sessions | List recent review sessions |
| GET | /intelligence/review-sessions/current | Get current week's session |
| PATCH | /intelligence/review-sessions/{id} | Update session link/status |
| POST | /intelligence/review-sessions/finalize | Finalize current week's session |
| GET | /intelligence/review-sessions/init-data | Get session initialization payload |
| POST | /intelligence/debrief | Create a debrief record |
| GET | /intelligence/debrief | List debrief records for current week |
| PATCH | /intelligence/debrief/{id} | Update debrief response/insight |
| POST | /intelligence/debrief/seed | Seed default debrief questions |

## Dependencies

- Feature 020 (Friday Strategic Execution Update)
- Feature 021 (Strategic Signal System)
- APScheduler (for scheduled Friday execution)
