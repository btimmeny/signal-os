# Feature 017: Weekly Platform Alignment Memo

## Summary

Adds a Weekly Platform Alignment Memo system that generates structured leadership memos from the current dashboard state. The system introduces Platform Leads as named individuals responsible for platform domains, and Leadership Memos as weekly artifacts that summarize progress, priorities, and focus areas grouped by lead.

## Motivation

Leadership needs a concise weekly view that:
- Aligns the team on what matters this week
- Summarizes progress across platform domains
- Groups work by responsible lead
- Creates a historical record of execution
- Remains a 5-minute read

## New Entities

### Platform Lead

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `name` | String | Lead's name (e.g., "Matteo") |
| `role` | String | Role title (e.g., "Head of Platform Engineering") |
| `focus_area` | String | Domain focus (e.g., "Infrastructure, CI/CD") |
| `description` | Text | Optional longer description |
| `initiative_ids` | JSON | Optional list of initiative UUIDs this lead owns |
| `active` | Boolean | Whether this lead is currently active |
| `created_at` | Timestamp | When the lead was created |

Default leads: Matteo, Mike, Sterren, Marina, Deepak.

### Leadership Memo

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `week_start_date` | Timestamp | Monday of the memo's week |
| `created_at` | Timestamp | When the memo was generated |
| `author` | String | Who generated/authored the memo |
| `status` | Enum | DRAFT, FINALIZED, SENT |
| `strategic_objective` | Text | The overarching objective |
| `current_priorities` | JSON | List of current priority items |
| `progress_summary` | Text | Summary of progress |
| `focus_next_week` | JSON | List of next week's focus items |
| `success_criteria` | JSON | List of success criteria |
| `lead_updates` | JSON | Dict mapping lead names to their updates |
| `dashboard_snapshot` | JSON | Snapshot of dashboard state (top_focus, needs_decision, due_soon, active_workstreams) |
| `audience` | JSON | List of lead names |

## New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/leads/create` | Create a platform lead |
| POST | `/leads/update` | Update a platform lead |
| GET | `/leads/list` | List platform leads (optional active_only filter) |
| POST | `/leads/seed` | Seed platform leads from a list |
| POST | `/memos/generate` | Generate a weekly memo from dashboard state |
| POST | `/memos/update` | Update a memo (status, fields) |
| GET | `/memos/list` | List memos (optional status filter) |
| GET | `/memos/get` | Get a single memo by ID |
| GET | `/memos/render` | Render a memo as formatted markdown text |

## Memo Generation Logic

When `/memos/generate` is called:
1. Pull dashboard state (top focus items, due soon items, active workstreams)
2. Pull all active platform leads
3. Group initiatives and tasks by platform lead
4. Generate memo template with sections: Strategic Objective, Current Priorities, Platform Updates (per lead), Focus for Next Week, Success Criteria
5. Save as DRAFT

## Tests

25 new tests covering:
- Platform lead CRUD (create, update, list, seed, idempotency)
- Memo generation (empty, with author, custom objective, dashboard capture, lead grouping)
- Memo CRUD (update, list, filter by status, get, not found)
- Memo rendering (formatted text output, with leads)
- End-to-end flow (seed leads -> create tasks -> generate -> finalize -> render)
- Auth enforcement
