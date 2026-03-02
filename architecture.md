# Signal OS -- Architecture

## 1. System Overview

Signal OS is a single-service Python application backed by PostgreSQL. It exposes a REST API via FastAPI and runs an optional background worker for reminder dispatch. The system is containerized with Docker and deployed to Railway.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Clients                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ ChatGPT      │  │ curl / HTTP  │  │ Future Clients       │   │
│  │ (Actions)    │  │ Clients      │  │ (Web UI, Mobile)     │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘   │
│         │                 │                     │               │
│         └─────────────────┼─────────────────────┘               │
│                           │                                     │
│                    X-API-Key Auth                                │
│                           │                                     │
│                           ▼                                     │
│              ┌────────────────────────┐                          │
│              │   FastAPI Application  │                          │
│              │       (Port 8300)      │                          │
│              └───────────┬────────────┘                          │
│                          │                                      │
│              ┌───────────┴────────────┐                          │
│              │     PostgreSQL 16      │                          │
│              │   (Alembic-managed)    │                          │
│              └────────────────────────┘                          │
│                          ▲                                      │
│              ┌───────────┴────────────┐                          │
│              │   Reminder Worker      │                          │
│              │  (Background Process)  │                          │
│              └────────────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Project Structure

```
signal-os/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, routes, auth middleware
│   ├── db.py                    # SQLAlchemy engine, session factory, Base
│   ├── models.py                # ORM models (Commitment, Reminder) + enums
│   ├── schemas.py               # Pydantic request/response schemas + enums
│   ├── worker.py                # Reminder polling worker (loop or one-shot)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── commitments.py       # Commitment CRUD + query logic
│   │   └── reminders.py         # Reminder CRUD + dispatch logic
│   └── integrations/
│       ├── __init__.py
│       └── whatsapp.py          # Mock WhatsApp sender (swap for Twilio)
├── alembic/
│   ├── env.py                   # Alembic environment config
│   ├── script.py.mako           # Migration template
│   └── versions/
│       ├── 001_initial_schema.py  # Initial migration
│       ├── 002_add_incident_urgency.py  # Add INCIDENT to urgency enum
│       ├── 003_add_admin_urgency.py    # Add ADMIN to urgency enum
│       ├── 004_add_priority_order.py   # Add priority_order column
│       └── 005_add_commitment_comments.py  # Add commitment_comments table
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Test fixtures (SQLite, TestClient)
│   ├── test_commitments.py      # Commitment endpoint tests
│   └── test_reminders.py        # Reminder endpoint tests
├── alembic.ini                  # Alembic configuration
├── docker-compose.yml           # Local dev environment (Postgres + API)
├── Dockerfile                   # Production container image
├── openapi.yaml                 # OpenAPI 3.1 spec for ChatGPT Actions
├── railway.toml                 # Railway deployment config
└── requirements.txt             # Python dependencies
```

## 3. Layer Architecture

The application follows a three-layer architecture:

### 3.1 API Layer (`app/main.py`)

- **Framework:** FastAPI with Uvicorn ASGI server
- **Responsibilities:**
  - Route definition and HTTP request handling
  - Authentication middleware (X-API-Key validation)
  - Request validation via Pydantic schemas
  - Response serialization
  - Dependency injection of database sessions

The API layer delegates all business logic to the service layer. Routes are thin -- they parse requests, call service functions, and return serialized responses.

### 3.2 Service Layer (`app/services/`)

- **`commitments.py`** -- Commitment CRUD and query operations
  - `open_commitment()` -- Create a new commitment
  - `close_commitment()` -- Close by ID or title match (with disambiguation)
  - `update_commitment()` -- Partial field updates
  - `list_open()` -- All non-CLOSED commitments
  - `set_priority()` -- Set a commitment's priority_order with automatic reordering
  - `list_priorities()` -- All ranked commitments sorted by priority_order
  - `query_commitments()` -- Filtered search (person, status, urgency, channel, dates, text)

- **`comments.py`** -- Commitment comment operations
  - `add_comment()` -- Add a timestamped comment to a commitment
  - `list_comments()` -- List all comments for a commitment, ordered oldest first

- **`reminders.py`** -- Reminder lifecycle
  - `create_reminder()` -- Schedule a new reminder
  - `get_due_reminders()` -- Find all due, unsent reminders
  - `dispatch_due_reminders()` -- Send due reminders via integrations and mark sent

The service layer contains all business logic and directly interacts with SQLAlchemy models. It receives database sessions from the API layer via dependency injection.

### 3.3 Data Layer (`app/db.py`, `app/models.py`)

- **Engine:** SQLAlchemy 2.0 with `psycopg` (v3) driver for PostgreSQL
- **Session management:** `sessionmaker` with `get_db()` generator for FastAPI dependency injection
- **Models:**
  - `Commitment` -- Primary entity with status/urgency/channel enums, timestamps, and person/org metadata
  - `CommitmentComment` -- Timestamped note linked to a commitment for tracking history
  - `Reminder` -- Linked to `Commitment` via foreign key with cascade delete
- **Relationships:**
  - `Commitment.reminders` (one-to-many, joined eager loading, cascade delete-orphan)
  - `Commitment.comments` (one-to-many, select loading, cascade delete-orphan, ordered by created_at)

### 3.4 Integration Layer (`app/integrations/`)

- **`whatsapp.py`** -- Mock implementation that logs to console
- **Interface:** `send_whatsapp(target: str, message: str) -> dict`
- **Design intent:** Swap this module for a real Twilio client without changing callers

## 4. Authentication

Authentication is handled via HTTP middleware, not per-route decorators:

1. Every incoming request passes through `api_key_middleware`
2. Requests to `/health`, `/docs`, `/openapi.json`, `/redoc` are exempt
3. All other requests must include `X-API-Key` header matching `AGENT_API_KEY` env var
4. Invalid or missing keys return `401 Unauthorized`

This is a single-tenant, single-key model suitable for agent-to-API communication.

## 5. Database

### 5.1 Schema

Three tables managed by Alembic migrations:

**`commitments`**
- Primary key: UUID (server-generated via `gen_random_uuid()`)
- Indexed columns: `title`, `status`, `person`, `due_at`
- Enum types: `commitment_status`, `urgency`, `channel_type`
- Timestamps: `opened_at`, `closed_at`, `due_at`, `last_touched_at`
- Additional columns: `priority_order` (nullable integer for explicit ranking)

**`commitment_comments`**
- Primary key: UUID (server-generated)
- Foreign key: `commitment_id` references `commitments.id` with `ON DELETE CASCADE`
- Indexed columns: `commitment_id`
- Columns: `body` (text, not null), `author` (varchar, nullable), `created_at` (timestamptz, not null)

**`reminders`**
- Primary key: UUID (server-generated)
- Foreign key: `commitment_id` references `commitments.id` with `ON DELETE CASCADE`
- Indexed columns: `commitment_id`, `remind_at`

### 5.2 Migrations

- Managed by Alembic with revision chain: `001` (initial schema) -> `002` (add INCIDENT urgency) -> `003` (add ADMIN urgency) -> `004` (add priority_order column) -> `005` (add commitment_comments table)
- Migrations run automatically on container startup (`alembic upgrade head`)
- `alembic/env.py` overrides the DB URL from `DATABASE_URL` env var at runtime

### 5.3 Connection Management

- SQLAlchemy engine with `pool_pre_ping=True` for connection health checks
- PostgreSQL URL is rewritten from `postgresql://` to `postgresql+psycopg://` to use the psycopg v3 driver
- SQLite URLs (used in tests) are passed through unchanged

## 6. Background Worker

The reminder worker (`app/worker.py`) runs as a separate process:

- **Loop mode:** Polls every `WORKER_INTERVAL` seconds (default: 60), calling `dispatch_due_reminders()`
- **One-shot mode:** `--once` flag runs a single poll cycle and exits
- **Error handling:** Exceptions in a poll cycle are logged but do not crash the worker
- **Database access:** Creates its own `SessionLocal` instance (independent of the FastAPI dependency injection)

The worker and the API server share the same database and the same service/integration code.

## 7. Deployment

### 7.1 Local Development

Docker Compose provides:
- **PostgreSQL 16 Alpine** on port 5433 (mapped from container 5432) with health checks
- **API service** on port 8300, runs `alembic upgrade head` then starts Uvicorn
- Named volume `pgdata` for database persistence

### 7.2 Production (Railway)

- **Build:** Dockerfile-based (`python:3.12-slim`)
- **Startup:** `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Restart policy:** ON_FAILURE with max 5 retries
- **Production URL:** `https://signal-os-api-production.up.railway.app`

## 8. Testing

- **Framework:** pytest with `pytest-asyncio`
- **Database:** SQLite in-memory with `StaticPool` (all threads see the same DB)
- **Fixtures:**
  - `db_session` -- Creates/drops tables per test function
  - `client` -- FastAPI `TestClient` wired to the test DB session via dependency override
- **Auth:** Tests use `X-API-Key: test-key` (set via env var in `conftest.py`)
- **Coverage:** 9 commitment tests, 3 reminder tests covering CRUD, edge cases (409 disambiguation), and dispatch lifecycle

## 9. Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| FastAPI | 0.115.0 | Web framework |
| Uvicorn | 0.30.6 | ASGI server |
| SQLAlchemy | 2.0.35 | ORM and database toolkit |
| Alembic | 1.13.3 | Database migrations |
| psycopg[binary] | 3.2.3 | PostgreSQL driver (v3) |
| Pydantic | 2.9.2 | Data validation and serialization |
| pydantic-settings | 2.5.2 | Settings management |
| python-dotenv | 1.0.1 | .env file loading |
| httpx | 0.27.2 | HTTP client (available for future integrations) |
| pytest | 8.3.3 | Testing framework |
| pytest-asyncio | 0.24.0 | Async test support |

## 10. Key Design Decisions

1. **Thin routes, fat services:** Routes only handle HTTP concerns; all business logic lives in the service layer.
2. **Enum duplication:** Enums are defined in both `models.py` (SQLAlchemy) and `schemas.py` (Pydantic) to keep the ORM and API layers decoupled.
3. **Mock-first integrations:** The WhatsApp integration uses a simple function interface so it can be replaced without refactoring callers.
4. **Computed fields at read time:** `days_open` is calculated when building the response, not stored in the database, ensuring it is always accurate.
5. **Single API key:** The MVP uses a single shared key rather than per-user auth, appropriate for a personal tool consumed by one AI agent.
6. **Joined eager loading:** `Commitment.reminders` uses `lazy="joined"` to avoid N+1 queries when dispatching reminders.
7. **Cascade deletes:** Deleting a commitment automatically removes its reminders via `ON DELETE CASCADE` at both the ORM and database levels.
