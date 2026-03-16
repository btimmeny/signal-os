# Feature 021: Strategic Signal System

## Overview

Every time a task or commitment is opened or closed, the system automatically evaluates how that action contributes to the broader platform initiatives and strategic objectives. This creates a continuous feedback loop between execution and strategy.

## Data Model

### New Fields on Commitment
- `strategic_contribution_note` (Text, nullable) — Generated when a task is opened. Explains how the task supports an initiative and contributes to platform strategy.
- `execution_impact_note` (Text, nullable) — Generated when a task is closed. Explains why the completion matters to platform strategy.

### New Table: `strategic_signals`
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| commitment_id | UUID (FK) | Reference to the commitment |
| initiative_id | UUID (FK, nullable) | Linked initiative |
| theme_id | UUID (FK, nullable) | Linked strategic theme |
| event_type | String(32) | OPENED or CLOSED |
| strategic_contribution | Text | The contribution note |
| execution_impact | Text | The impact note (CLOSED events) |
| is_high_signal | Integer | 1 if high-signal, 0 otherwise |
| signal_category | String(128) | Category classification |
| created_at | DateTime | When the signal was recorded |

## Signal Generation

### Task Open Event
When a commitment is opened, the system:
1. Determines which initiative the task supports (via initiative links)
2. Determines which strategic theme it contributes to (via initiative's theme)
3. Classifies the signal category (infrastructure, tooling_integration, agent_capability, pilot_progress, new_capability, knowledge_platform)
4. Generates a Strategic Contribution Note
5. Stores the note on the commitment and creates a StrategicSignal record

### Task Close Event
When a commitment is closed, the system:
1. Determines initiative and theme context
2. Generates an Execution Impact Statement
3. Determines if the closure is high-signal
4. Stores the impact note and creates a StrategicSignal record

### Unclear Contributions
If a task has no linked initiative or theme, the system flags it as unclear and generates a note indicating the task should be linked to an initiative or strategic theme.

## Signal Categories
- **new_capability** — New features, releases, launches
- **infrastructure** — Pipeline, deployment, architecture, framework
- **tooling_integration** — SDK, API, CLI, plugin integrations
- **pilot_progress** — POC, prototype, experiment, trial
- **agent_capability** — Agent, AI, LLM, automation improvements
- **knowledge_platform** — Documentation, wiki, index, graph

## High-Signal Detection
Tasks are marked high-signal when they:
- Are linked to an initiative AND contain strategic keywords
- Contain strong strategic keywords (infrastructure, platform, architecture, capability, release)

## API Endpoints
- `GET /signals/list` — List recent signals with optional filters (event_type, high_signal_only)
- `GET /signals/weekly-summary` — Aggregated weekly signal summary
- `GET /signals/commitment/{id}` — Signals for a specific commitment
- `GET /signals/{id}` — Get a single signal by ID

## Integration Points
- **Commitment Open** (`/commitments/open`) — Automatically generates open signal
- **Commitment Close** (`/commitments/close`) — Automatically generates close signal
- **Commitment Update** (`/commitments/update`) — Generates close signal if status changes to CLOSED
- **Friday Update** (Feature 020) — Signal aggregation enriches the weekly update with strategic signal data
- **Weekly Memo** (Feature 019) — Signals available for memo narrative generation

## Migration
- Alembic migration `015_add_strategic_signals.py`
