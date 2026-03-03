# Signal OS -- Product Specification

## 1. Overview

Signal OS is a personal commitment log system that captures, tracks, and surfaces commitments extracted from everyday conversations. It provides a structured API for creating, querying, updating, and closing commitments, along with a reminder subsystem that ensures nothing falls through the cracks.

The system is designed to operate as a backend service consumed by AI agents (specifically ChatGPT via Actions), enabling natural-language-driven commitment management.

## 2. Problem Statement

Professionals make commitments constantly -- in emails, Slack messages, meetings, calls, and texts. These commitments are scattered across channels and easily forgotten. There is no single system that:

- Captures commitments from any channel in a unified format
- Tracks their status and urgency over time
- Reminds the user before things slip
- Is queryable by person, urgency, channel, or free text

Signal OS solves this by providing a structured commitment log with reminder capabilities, accessible via a REST API that AI agents can call directly from conversation context.

## 3. Target Users

- **Primary:** Individuals who manage many interpersonal commitments across channels (managers, founders, consultants, account executives)
- **Integration consumer:** ChatGPT (via Actions/OpenAPI), with future extensibility to other AI agents or frontends

## 4. Core Concepts

### 4.1 Commitment

A commitment is a promise, task, or follow-up tied to a person or organization. It is the central entity in Signal OS.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Auto-generated | Unique identifier |
| `title` | String (max 512) | Yes | Short description of the commitment |
| `description` | Text | No | Longer context or notes |
| `status` | Enum | Yes (default: OPEN) | OPEN, WAITING, SNOOZED, CLOSED |
| `urgency` | Enum | No | INCIDENT, NOW, SOON, SCHEDULED, SOMEDAY, ADMIN |
| `person` | String | No | The person this commitment is with |
| `organization` | String | No | Associated organization |
| `channel_type` | Enum | No | email, slack, meeting, call, text, web, other |
| `channel_title` | String | No | Name/subject of the channel (e.g., email subject) |
| `channel_link` | String | No | URL or deep link to the source |
| `source_snippet` | Text | No | Verbatim excerpt from the conversation |
| `opened_at` | Timestamp | Yes (auto) | When the commitment was created |
| `closed_at` | Timestamp | Nullable | When the commitment was closed |
| `due_at` | Timestamp | Nullable | Optional deadline |
| `last_touched_at` | Timestamp | Yes (auto) | Last modification time |
| `priority_order` | Integer | No | Position in the overall priority list (1 = top) |
| `days_open` | Float | Computed at read | Elapsed days since opened (or until closed) |

### 4.3 Commitment Comment

A comment is a timestamped note attached to a commitment. Comments capture status updates, meeting notes, progress reports, or any context that helps track the history of a commitment.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Auto-generated | Unique identifier |
| `commitment_id` | UUID (FK) | Yes | The commitment this comment belongs to |
| `body` | Text | Yes | The comment content |
| `author` | String | No | Who wrote the comment |
| `created_at` | Timestamp | Yes (auto) | When the comment was created |

**Status lifecycle:**
- **OPEN** -- Active, needs action
- **WAITING** -- Blocked on someone else
- **SNOOZED** -- Intentionally deferred
- **CLOSED** -- Completed or cancelled

**Urgency levels:**
- **INCIDENT** -- Urgent, breaking in production right now
- **NOW** -- Immediate action required
- **SOON** -- Within the next few days
- **SCHEDULED** -- Has a specific due date
- **SOMEDAY** -- No time pressure
- **ADMIN** -- Get it done when you can (lowest priority)

### 4.4 Strategic Objective

A strategic objective is an annual goal that commitments (action items) drive toward. Objectives provide the "why" behind individual tasks.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Auto-generated | Unique identifier |
| `title` | String (max 512) | Yes | Short description of the objective |
| `description` | Text | No | Longer context or details |
| `year` | Integer | Yes | The year this objective applies to |
| `status` | Enum | Yes (default: ACTIVE) | ACTIVE, COMPLETED, DEFERRED, CANCELLED |
| `created_at` | Timestamp | Yes (auto) | When the objective was created |
| `updated_at` | Timestamp | Yes (auto) | Last modification time |

**Objective statuses:**
- **ACTIVE** -- Currently being pursued
- **COMPLETED** -- Successfully achieved
- **DEFERRED** -- Postponed to a future period
- **CANCELLED** -- No longer relevant

### 4.5 Objective-Commitment Link

A link connects a commitment (action item) to a strategic objective, recording why this action supports the goal.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Auto-generated | Unique identifier |
| `objective_id` | UUID (FK) | Yes | The strategic objective |
| `commitment_id` | UUID (FK) | Yes | The action item |
| `rationale` | Text | No | Why this action drives this objective |
| `created_at` | Timestamp | Yes (auto) | When the link was created |

### 4.6 Objective Update

An update is general commentary on an objective, not tied to a specific task. Used for meeting notes, market observations, strategic shifts, etc.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Auto-generated | Unique identifier |
| `objective_id` | UUID (FK) | Yes | The objective this update is about |
| `body` | Text | Yes | The update content |
| `author` | String | No | Who wrote the update |
| `created_at` | Timestamp | Yes (auto) | When the update was created |

### 4.7 Status Report

A status report is a stored artifact summarizing progress for a time period (weekly, monthly, quarterly, annual).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Auto-generated | Unique identifier |
| `period_type` | Enum | Yes | WEEKLY, MONTHLY, QUARTERLY, ANNUAL |
| `period_start` | Timestamp | Yes | Start of the reporting period |
| `period_end` | Timestamp | Yes | End of the reporting period |
| `body` | Text | Yes | The report content |
| `created_at` | Timestamp | Yes (auto) | When the report was created |

### 4.8 Reminder

A reminder is a scheduled notification tied to a commitment. When the reminder time arrives, the system dispatches a message via the configured delivery channel.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Auto-generated | Unique identifier |
| `commitment_id` | UUID (FK) | Yes | The commitment this reminder is for |
| `remind_at` | Timestamp | Yes | When to fire the reminder |
| `sent_at` | Timestamp | Nullable | When the reminder was actually sent |
| `delivery_channel` | String | Yes (default: whatsapp) | Channel for delivery |
| `delivery_target` | String | No | Recipient identifier (e.g., phone number) |
| `message` | Text | No | Custom message body (defaults to commitment title) |

## 5. Functional Requirements

### 5.1 Commitment Management

| ID | Requirement | Status |
|----|-------------|--------|
| FR-1 | Create a commitment with title (required) and optional metadata | Implemented |
| FR-2 | Close a commitment by UUID | Implemented |
| FR-3 | Close a commitment by exact title match (with optional person filter) | Implemented |
| FR-4 | Return 409 with candidate list when title-based close matches multiple commitments | Implemented |
| FR-5 | Update any subset of commitment fields by UUID | Implemented |
| FR-6 | List all non-CLOSED commitments, ordered by oldest first | Implemented |
| FR-7 | Query commitments with filters: person (fuzzy), status, urgency, channel_type, due date range, opened date range, free text search across title and description | Implemented |
| FR-8 | Compute `days_open` dynamically at read time | Implemented |
| FR-16 | Set a commitment's priority_order, automatically shifting other items to maintain contiguous ranking | Implemented |
| FR-17 | List all non-CLOSED commitments ranked by priority_order | Implemented |
| FR-18 | Add a timestamped comment to a commitment with optional author | Implemented |
| FR-19 | List all comments for a commitment, ordered oldest to newest | Implemented |

### 5.2 Strategic Objectives

| ID | Requirement | Status |
|----|-------------|--------|
| FR-20 | Create a strategic objective with title, year, optional description and status | Implemented |
| FR-21 | Update an objective's title, description, year, or status | Implemented |
| FR-22 | Get a single objective by ID | Implemented |
| FR-23 | List objectives with optional year and status filters | Implemented |

### 5.3 Objective-Commitment Linking

| ID | Requirement | Status |
|----|-------------|--------|
| FR-24 | Link a commitment to an objective with optional rationale (idempotent) | Implemented |
| FR-25 | Unlink a commitment from an objective | Implemented |
| FR-26 | List all commitments linked to an objective | Implemented |
| FR-27 | List all objectives linked to a commitment | Implemented |

### 5.4 Objective Updates

| ID | Requirement | Status |
|----|-------------|--------|
| FR-28 | Add a general commentary update to an objective | Implemented |
| FR-29 | List all updates for an objective, ordered oldest first | Implemented |

### 5.5 Status Reports

| ID | Requirement | Status |
|----|-------------|--------|
| FR-30 | Create a status report with period type, date range, and body | Implemented |
| FR-31 | List status reports with optional period type filter | Implemented |
| FR-32 | Get a single status report by ID | Implemented |
| FR-33 | Gather aggregated status data for a period (objectives, linked commitments with comments, objective updates, commitment activity) | Implemented |

### 5.6 Task Dashboard

| ID | Requirement | Status |
|----|-------------|--------|
| FR-34 | Provide a single GET endpoint that returns all non-CLOSED commitments organized by priority rank, strategic objective, and urgency grouping | Implemented |
| FR-35 | Include GPT training instructions in the OpenAPI spec to prevent hallucination and ensure the dashboard is always used as the canonical task source | Implemented |

### 5.7 Reminder Management

| ID | Requirement | Status |
|----|-------------|--------|
| FR-9 | Create a reminder linked to a commitment with a future (or past) `remind_at` timestamp | Implemented |
| FR-10 | List all due and unsent reminders (`remind_at <= now` and `sent_at IS NULL`) | Implemented |
| FR-11 | Dispatch all due reminders: send via integration, mark `sent_at` | Implemented |
| FR-12 | Background worker polls for due reminders on a configurable interval | Implemented |

### 5.3 Authentication

| ID | Requirement | Status |
|----|-------------|--------|
| FR-13 | All endpoints (except `/health`, `/docs`, `/openapi.json`, `/redoc`) require a valid `X-API-Key` header | Implemented |
| FR-14 | Return 401 for missing or invalid API key | Implemented |

### 5.4 Health Check

| ID | Requirement | Status |
|----|-------------|--------|
| FR-15 | `/health` endpoint returns database connectivity status (no auth required) | Implemented |

## 6. Non-Functional Requirements

| ID | Requirement | Details |
|----|-------------|---------|
| NFR-1 | **Database** | PostgreSQL 16 for production; SQLite in-memory for tests |
| NFR-2 | **Migrations** | Alembic-managed, run automatically on container start |
| NFR-3 | **Containerization** | Docker + Docker Compose for local development |
| NFR-4 | **Deployment** | Railway (Dockerfile-based build, ON_FAILURE restart policy) |
| NFR-5 | **API Standard** | OpenAPI 3.1 spec provided for ChatGPT Actions integration |
| NFR-6 | **Testing** | pytest with FastAPI TestClient; SQLite in-memory with StaticPool |
| NFR-7 | **Logging** | Structured logging via Python `logging` module |

## 7. API Surface

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (no auth) |
| POST | `/commitments/open` | Create a new commitment |
| GET | `/commitments/open` | List all open (non-CLOSED) commitments |
| POST | `/commitments/close` | Close by ID or title match |
| POST | `/commitments/update` | Partial update by ID |
| GET | `/commitments/query` | Query with filters |
| POST | `/commitments/set_priority` | Set a commitment's position in the priority list |
| GET | `/commitments/priorities` | List all open commitments ranked by priority |
| GET | `/commitments/dashboard` | Comprehensive organized view of all open tasks |
| POST | `/commitments/comment` | Add a comment to a commitment |
| GET | `/commitments/comments` | List all comments for a commitment |
| GET | `/commitments/objectives` | List all objectives linked to a commitment |
| POST | `/objectives/create` | Create a strategic objective |
| POST | `/objectives/update` | Update an objective's fields |
| GET | `/objectives/list` | List objectives (filter by year/status) |
| GET | `/objectives/get` | Get a single objective by ID |
| POST | `/objectives/link` | Link a commitment to an objective |
| POST | `/objectives/unlink` | Unlink a commitment from an objective |
| GET | `/objectives/links` | List commitments linked to an objective |
| POST | `/objectives/update_note` | Add general commentary to an objective |
| GET | `/objectives/updates` | List all updates for an objective |
| POST | `/status/report` | Create a status report |
| GET | `/status/report` | Get a single status report by ID |
| GET | `/status/reports` | List status reports (filter by period) |
| POST | `/status/data` | Gather aggregated status data for a period |
| POST | `/reminders/create` | Schedule a reminder |
| GET | `/reminders/due` | List due unsent reminders |
| POST | `/reminders/dispatch_due` | Dispatch all due reminders |

### Authentication

All protected endpoints require the `X-API-Key` header. The key is configured via the `AGENT_API_KEY` environment variable.

## 8. Integration Points

### 8.1 ChatGPT Actions (Current)

The `openapi.yaml` file is importable into ChatGPT's Actions configuration. The AI agent can then create, query, close, and manage commitments directly from conversation.

### 8.2 WhatsApp Reminders (MVP -- Mock)

The current WhatsApp integration is a mock that logs messages to the console. The interface (`send_whatsapp(target, message)`) is designed to be swapped with a real Twilio/WhatsApp Business API client without changing any callers.

## 9. Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://signalos:signalos@localhost:5432/signal_os` | Database connection string |
| `AGENT_API_KEY` | `dev-key-change-me` | API key for authentication |
| `HOST` | `0.0.0.0` | Server bind host |
| `PORT` | `8300` | Server bind port |
| `WORKER_INTERVAL` | `60` | Seconds between reminder worker poll cycles |

## 10. Future Considerations

- Replace mock WhatsApp sender with Twilio WhatsApp Business API
- Add support for additional delivery channels (email, Slack, SMS)
- Multi-user / multi-tenant support
- Recurring reminders
- Commitment tagging and categorization
- AI-generated status report narratives from gathered status data
- Analytics and reporting (commitments per person, average days open, etc.)
- Webhook support for external event triggers
- Rate limiting and API key rotation
