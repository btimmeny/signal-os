# Feature 020: Friday Strategic Execution Update — Plan

## Phases

### Phase 1: Data Model
- Add `UpdateStatus` enum to models.py
- Add `WeeklyStrategyUpdate` model with fields for narratives, scoring, continuity, forwardable body, signal snapshot
- Create migration 014

### Phase 2: Signal Extraction
- Build `extract_signals()` function querying past 7 days
- Extract: closed tasks, opened tasks, total open, overdue, due soon, active initiatives, completed initiatives, stalled initiatives, active themes, recent comments, priorities

### Phase 3: Strategy Confidence Score
- Build `_compute_confidence_score()` with four weighted components
- Execution Progress (35%), Momentum (25%), Alignment (20%), Friction (20% inverted)
- Build `_compute_trend()` for week-over-week comparison

### Phase 4: Narrative Generation
- Build three narrative generators with distinct framings
- Execution Progress, Momentum, Alignment
- Each: 3 prose paragraphs, ~150-200 words, no bullet lists
- Build `_select_recommended_narrative()` with reason

### Phase 5: Email & Distribution
- Build `compose_update_email()` with all 8 sections
- Build `send_update_email()` via Gmail SMTP
- Build `_build_forwardable_body()` clean version

### Phase 6: Endpoint & Schema
- Add `FridayUpdateResponse` schema
- Add `POST /friday-update`, `GET /friday-update/latest`, `GET /friday-update/list`

### Phase 7: Tests & Documentation
- 38 tests covering all components
- Feature folder with specification, plan, task docs
- Update specification.md

## Dependencies
- Existing models: Commitment, Initiative, StrategicTheme, CommitmentComment
- Gmail credentials (optional — email skipped if not configured)
