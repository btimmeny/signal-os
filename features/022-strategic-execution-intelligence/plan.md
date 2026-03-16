# Feature 022: Strategic Execution Intelligence — Implementation Plan

## Overview

Build a system that automatically converts task activity into strategic insight and produces scheduled weekly leadership updates with durable memory across sessions.

## Implementation Steps

### Step 1: Database Schema
- Create migration 016 with 5 new tables (strategic_contribution_notes, execution_impact_notes, strategic_narratives, strategy_confidence_history, weekly_narratives)
- Extend strategic_signals table with confidence_weight column
- Add SQLAlchemy models for all new tables

### Step 2: Core Service (strategic_intelligence.py)
- Contribution note recording on task open (with idempotency)
- Impact note recording on task close (with idempotency)
- Strategic narrative building (week-over-week)
- Confidence history recording with trend calculation
- Weekly narrative generation (3 drafts per week)
- Integrated intelligence update pipeline
- Email composition
- APScheduler setup for Friday 12:00 PM

### Step 3: API Layer
- Add Pydantic schemas for all new response types
- Add 10 new endpoints for intelligence CRUD and generation
- Integrate contribution/impact note recording into task open/close flows

### Step 4: Testing
- 56 comprehensive tests covering all sections
- Idempotency verification
- Session independence verification
- API endpoint testing
- Scheduler testing

### Step 5: Documentation
- Feature specification
- Implementation plan
- Task tracking document
- Update specification.md

## Dependencies
- Feature 020 (Friday Strategic Execution Update) — for base update generation
- Feature 021 (Strategic Signal System) — for signal classification
- APScheduler — for scheduled execution

### Step 6: ChatGPT Review Sessions (Section 6)
- Create migration 017 with weekly_review_sessions and strategy_debrief_records tables
- Add WeeklyReviewSession and StrategyDebriefRecord models
- Idempotent session creation (one per week)
- Session initialization data payload for ChatGPT preloading
- Review session section in email composition
- 10 new API endpoints for session and debrief management

### Step 7: Strategy Debrief (Section 7)
- Default 4 high-leverage debrief questions
- Debrief record CRUD with idempotent seeding
- Response and derived insight storage
- Integration into Friday update pipeline
- 43 new comprehensive tests

## Key Design Decisions
- All strategic commentary persisted in dedicated tables (not session memory)
- Idempotency enforced via query-before-insert pattern
- Three narrative framings per week for leadership flexibility
- Confidence score uses weighted components (40/25/20 + friction penalty)
- Trend direction uses ±5 threshold for meaningful change detection
- Review sessions are idempotent per week (one session per week_date)
- Debrief responses stored in DB, not session memory (durable memory)
- Email composition conditionally includes review session section
