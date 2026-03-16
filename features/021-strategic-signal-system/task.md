# Feature 021: Strategic Signal System — Task

## Status: Complete

## Summary
Implemented the Strategic Signal System that automatically evaluates how each task/commitment opening and closing contributes to the broader platform initiatives and strategic objectives.

## What Was Built
1. **StrategicSignal model** — Tracks every task open/close event with initiative context, theme context, contribution/impact notes, high-signal classification, and signal category
2. **strategic_signals.py service** — Core logic for signal generation, classification, querying, and weekly aggregation
3. **Endpoint integration** — `/commitments/open`, `/commitments/close`, and `/commitments/update` now auto-generate strategic signals
4. **Signal query endpoints** — `/signals/list`, `/signals/weekly-summary`, `/signals/commitment/{id}`, `/signals/{id}`
5. **Friday update integration** — Strategic signals enrich the weekly update signal snapshot
6. **Migration 015** — Adds `strategic_contribution_note` and `execution_impact_note` to commitments, creates `strategic_signals` table

## Test Coverage
- 44 new tests across 8 test classes
- All 230 tests pass (186 existing + 44 new)

## Post-Merge Steps
1. Deploy to Railway
2. Migration 015 runs automatically on startup
3. All new task opens/closes will generate strategic signals
4. Use `/signals/weekly-summary` to view aggregated signal data
5. Friday updates will automatically include strategic signal context
