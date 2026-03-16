# Feature 021: Strategic Signal System — Implementation Plan

## Objective
Build an event-driven strategic signal system that automatically evaluates how each task opening and closing contributes to the broader platform initiatives and strategic objectives.

## Implementation Steps

### 1. Data Model
- Add `strategic_contribution_note` and `execution_impact_note` fields to the Commitment model
- Create `StrategicSignal` model with commitment, initiative, theme references, event type, contribution/impact text, high-signal flag, and category
- Create Alembic migration 015

### 2. Strategic Signals Service (`app/services/strategic_signals.py`)
- Signal classification (6 categories: new_capability, infrastructure, tooling_integration, pilot_progress, agent_capability, knowledge_platform)
- High-signal detection based on keywords and initiative linkage
- `record_open_signal()` — generates Strategic Contribution Note on task open
- `record_close_signal()` — generates Execution Impact Note on task close
- Query functions: by commitment, by period, high-signal only, unclear signals
- Weekly aggregation with grouping by initiative, theme, and category
- Formatted summary text generation

### 3. Endpoint Integration
- `/commitments/open` — auto-generates open signal after commitment creation
- `/commitments/close` — auto-generates close signal after commitment closure
- `/commitments/update` — generates close signal when status changes to CLOSED

### 4. Signal Query Endpoints
- `GET /signals/list` — list with filters (event_type, high_signal_only, limit)
- `GET /signals/weekly-summary` — aggregated weekly summary
- `GET /signals/commitment/{id}` — signals for a specific commitment
- `GET /signals/{id}` — single signal by ID

### 5. Friday Update Integration
- Enrich Friday update signal snapshot with strategic signal aggregation data
- Include high-signal titles, initiative/theme groupings, unclear count

### 6. Testing
- 44 new tests covering signal generation, classification, endpoints, service functions, note content, and Friday update integration

## Files Changed
- `app/models.py` — StrategicSignal model, SignalEventType enum, Commitment fields
- `app/schemas.py` — StrategicSignalResponse, SignalSummaryResponse, CommitmentResponse fields
- `app/services/strategic_signals.py` — New service (core logic)
- `app/main.py` — Signal generation in endpoints, new signal query endpoints
- `app/services/friday_update.py` — Strategic signal enrichment
- `alembic/versions/015_add_strategic_signals.py` — Migration
- `tests/conftest.py` — Register StrategicSignal model
- `tests/test_strategic_signals.py` — 44 new tests
