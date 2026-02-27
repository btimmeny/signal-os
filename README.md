# Signal OS

Personal commitment log system. Tracks commitments extracted from conversations, supports querying by person/status/urgency/channel, and sends reminders (WhatsApp mock in MVP).

Designed to connect to ChatGPT via Actions using the included `openapi.yaml`.

## Architecture

```
app/
├── main.py                    # FastAPI routes + X-API-Key auth
├── db.py                      # SQLAlchemy engine/session
├── models.py                  # ORM models (Commitment, Reminder)
├── schemas.py                 # Pydantic request/response schemas
├── worker.py                  # Reminder polling worker
├── services/
│   ├── commitments.py         # Commitment CRUD + query
│   └── reminders.py           # Reminder CRUD + dispatch
└── integrations/
    └── whatsapp.py            # Mock WhatsApp sender (swap for Twilio later)
```

## Setup

### 1. Clone and configure

```bash
git clone <repo-url>
cd signal-os
cp .env.example .env
# Edit .env — set AGENT_API_KEY to something secure
```

### 2. Start with Docker Compose

```bash
docker compose up --build
```

This starts Postgres + the API on port 8300 and runs Alembic migrations automatically.

### 3. Run migrations manually (if needed)

```bash
# With Postgres running:
alembic upgrade head
```

### 4. Run the API standalone

```bash
pip install -r requirements.txt
python -m app.main
```

### 5. Run the reminder worker

```bash
# Run once and exit
python -m app.worker --once

# Run in loop mode (checks every 60s)
python -m app.worker
```

### 6. Run tests

```bash
pip install -r requirements.txt
pytest -v
```

Tests use SQLite in-memory — no Postgres required.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://signalos:signalos@localhost:5432/signal_os` | Postgres connection string |
| `AGENT_API_KEY` | `dev-key-change-me` | API key for X-API-Key header auth |
| `HOST` | `0.0.0.0` | Server bind host |
| `PORT` | `8300` | Server bind port |
| `WORKER_INTERVAL` | `60` | Seconds between worker poll cycles |

## API Endpoints

All endpoints except `/health` require `X-API-Key` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/commitments/open` | Create a commitment |
| `POST` | `/commitments/close` | Close by ID or title match |
| `POST` | `/commitments/update` | Update partial fields |
| `GET` | `/commitments/open` | List all open commitments |
| `GET` | `/commitments/query` | Query with filters |
| `POST` | `/reminders/create` | Schedule a reminder |
| `GET` | `/reminders/due` | List due unsent reminders |
| `POST` | `/reminders/dispatch_due` | Dispatch all due reminders |

## Example curl Commands

```bash
API_KEY="dev-key-change-me"

# Health
curl http://localhost:8300/health

# Open a commitment
curl -X POST http://localhost:8300/commitments/open \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "title": "Follow up with Alice on Q3 proposal",
    "person": "Alice",
    "urgency": "SOON",
    "channel_type": "email"
  }'

# List open commitments
curl http://localhost:8300/commitments/open \
  -H "X-API-Key: $API_KEY"

# Close by ID
curl -X POST http://localhost:8300/commitments/close \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"commitment_id": "<uuid>"}'

# Close by title
curl -X POST http://localhost:8300/commitments/close \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"title": "Follow up with Alice on Q3 proposal"}'

# Update
curl -X POST http://localhost:8300/commitments/update \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"commitment_id": "<uuid>", "urgency": "NOW", "status": "WAITING"}'

# Query by person
curl "http://localhost:8300/commitments/query?person=Alice" \
  -H "X-API-Key: $API_KEY"

# Query by text search
curl "http://localhost:8300/commitments/query?text=proposal" \
  -H "X-API-Key: $API_KEY"

# Create a reminder
curl -X POST http://localhost:8300/reminders/create \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "commitment_id": "<uuid>",
    "remind_at": "2026-03-01T09:00:00Z",
    "message": "Ping Alice about the proposal"
  }'

# List due reminders
curl http://localhost:8300/reminders/due \
  -H "X-API-Key: $API_KEY"

# Dispatch due reminders (mock WhatsApp send)
curl -X POST http://localhost:8300/reminders/dispatch_due \
  -H "X-API-Key: $API_KEY"
```

## GPT Actions

Import `openapi.yaml` into ChatGPT Actions. Set the `X-API-Key` authentication header to your `AGENT_API_KEY`.

## Push to GitLab

```bash
git init
git remote add origin https://gitlab.com/<your-namespace>/signal-os.git
git add . && git commit -m "Initial MVP"
git push -u origin main
```

## Data Model

### Commitment

| Field | Type | Required |
|-------|------|----------|
| `id` | UUID | auto |
| `title` | string (512) | yes |
| `description` | text | no |
| `status` | OPEN/WAITING/SNOOZED/CLOSED | yes |
| `urgency` | NOW/SOON/SCHEDULED/SOMEDAY | no |
| `person` | string | no |
| `organization` | string | no |
| `channel_type` | email/slack/meeting/call/text/web/other | no |
| `channel_title` | string | no |
| `channel_link` | string | no |
| `source_snippet` | text | no |
| `opened_at` | timestamp | yes |
| `closed_at` | timestamp | nullable |
| `due_at` | timestamp | nullable |
| `last_touched_at` | timestamp | yes |
| `days_open` | float | computed at read |

### Reminder

| Field | Type | Required |
|-------|------|----------|
| `id` | UUID | auto |
| `commitment_id` | UUID (FK) | yes |
| `remind_at` | timestamp | yes |
| `sent_at` | timestamp | nullable |
| `delivery_channel` | string | yes (default: whatsapp) |
| `delivery_target` | string | no |
| `message` | text | no |

## License

MIT
