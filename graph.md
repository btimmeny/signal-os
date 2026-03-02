# Signal OS -- System Graphs

## 1. Request Flow

```
Client (ChatGPT / curl / etc.)
  │
  │  HTTP Request + X-API-Key header
  │
  ▼
┌──────────────────────────────────┐
│         api_key_middleware       │
│  (/health, /docs exempt)        │
│  Validates X-API-Key header     │
│  Returns 401 if invalid         │
└──────────────┬───────────────────┘
               │ (authenticated)
               ▼
┌──────────────────────────────────┐
│         FastAPI Router           │
│  main.py route handlers          │
│  Parses request, injects DB      │
│  session via Depends(get_db)     │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│         Service Layer            │
│  services/commitments.py         │
│  services/reminders.py           │
│  Business logic + DB queries     │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│         Data Layer               │
│  SQLAlchemy ORM (models.py)      │
│  PostgreSQL / SQLite             │
└──────────────────────────────────┘
```

## 2. Entity Relationship Diagram

```
┌─────────────────────────────────────────────────┐
│                  commitments                     │
├─────────────────────────────────────────────────┤
│  id              UUID          PK                │
│  title           VARCHAR(512)  NOT NULL, INDEX   │
│  description     TEXT          NULLABLE           │
│  status          ENUM          NOT NULL, INDEX   │
│                  (OPEN|WAITING|SNOOZED|CLOSED)   │
│  urgency         ENUM          NULLABLE           │
│                  (INCIDENT|NOW|SOON|SCHEDULED|   │
│                   SOMEDAY)                       │
│  person          VARCHAR(256)  NULLABLE, INDEX   │
│  organization    VARCHAR(256)  NULLABLE           │
│  channel_type    ENUM          NULLABLE           │
│                  (email|slack|meeting|call|       │
│                   text|web|other)                 │
│  channel_title   VARCHAR(256)  NULLABLE           │
│  channel_link    VARCHAR(1024) NULLABLE           │
│  source_snippet  TEXT          NULLABLE           │
│  opened_at       TIMESTAMPTZ   NOT NULL           │
│  closed_at       TIMESTAMPTZ   NULLABLE           │
│  due_at          TIMESTAMPTZ   NULLABLE, INDEX   │
│  last_touched_at TIMESTAMPTZ   NOT NULL           │
├─────────────────────────────────────────────────┤
│  1 ───────────────────────── * reminders         │
└─────────────────────────────────────────────────┘

                     │ ON DELETE CASCADE
                     │
                     ▼

┌─────────────────────────────────────────────────┐
│                  reminders                       │
├─────────────────────────────────────────────────┤
│  id               UUID          PK               │
│  commitment_id    UUID          FK, NOT NULL,    │
│                                 INDEX             │
│  remind_at        TIMESTAMPTZ   NOT NULL, INDEX  │
│  sent_at          TIMESTAMPTZ   NULLABLE          │
│  delivery_channel VARCHAR(64)   NOT NULL          │
│                                 (default:whatsapp)│
│  delivery_target  VARCHAR(256)  NULLABLE          │
│  message          TEXT          NULLABLE          │
└─────────────────────────────────────────────────┘
```

## 3. Commitment Lifecycle

```
                    ┌──────────┐
    POST /open      │          │
   ────────────────►│   OPEN   │
                    │          │
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
              ▼          ▼          ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │          │ │          │ │          │
        │ WAITING  │ │ SNOOZED  │ │  CLOSED  │
        │          │ │          │ │          │
        └────┬─────┘ └────┬─────┘ └──────────┘
             │            │              ▲
             │            │              │
             └────────────┴──────────────┘
                  POST /update
                  POST /close
```

- **OPEN** -- Default state on creation
- **WAITING** -- Set via update (blocked on someone)
- **SNOOZED** -- Set via update (intentionally deferred)
- **CLOSED** -- Set via close endpoint or update; records `closed_at` timestamp
- Transitions between OPEN, WAITING, and SNOOZED are reversible
- CLOSED is a terminal state (can be reopened via update if needed)

## 4. Reminder Dispatch Flow

```
┌─────────────────────────┐
│   Reminder Worker       │
│   (worker.py)           │
│                         │
│   Loop every 60s        │
│   or --once mode        │
└────────────┬────────────┘
             │
             │  calls dispatch_due_reminders()
             ▼
┌─────────────────────────┐
│   services/reminders.py │
│                         │
│   1. Query: remind_at   │
│      <= now AND         │
│      sent_at IS NULL    │
│                         │
│   2. For each due       │
│      reminder:          │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   integrations/         │
│   whatsapp.py           │
│                         │
│   send_whatsapp(        │
│     target, message     │
│   )                     │
│                         │
│   [MOCK: logs to        │
│    console]             │
└────────────┬────────────┘
             │
             │  on success
             ▼
┌─────────────────────────┐
│   Mark sent_at = now    │
│   Commit to DB          │
└─────────────────────────┘
```

## 5. Deployment Topology

```
┌──────────────────────────────────────────────────────┐
│                    Railway                            │
│                                                      │
│   ┌──────────────────────────────────────────────┐   │
│   │            Docker Container                   │   │
│   │                                               │   │
│   │   1. alembic upgrade head                     │   │
│   │   2. uvicorn app.main:app                     │   │
│   │      --host 0.0.0.0 --port $PORT              │   │
│   │                                               │   │
│   │   Restart: ON_FAILURE (max 5 retries)         │   │
│   └──────────────────────┬────────────────────────┘   │
│                          │                            │
│                          ▼                            │
│   ┌──────────────────────────────────────────────┐   │
│   │            PostgreSQL                         │   │
│   │   (Railway-managed or external)               │   │
│   └──────────────────────────────────────────────┘   │
│                                                      │
│   Public URL:                                        │
│   https://signal-os-api-production.up.railway.app    │
└──────────────────────────────────────────────────────┘


┌──────────────────────────────────────────────────────┐
│               Local Development                      │
│               (docker-compose.yml)                    │
│                                                      │
│   ┌──────────────────┐    ┌──────────────────────┐   │
│   │  postgres:16     │    │   api (Dockerfile)   │   │
│   │  Port 5433:5432  │◄───│   Port 8300:8300     │   │
│   │  Volume: pgdata  │    │   Runs migrations    │   │
│   │  Health checks   │    │   + uvicorn          │   │
│   └──────────────────┘    └──────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

## 6. API Route Map

```
                        /
                        │
          ┌─────────────┼──────────────┐
          │             │              │
      /health     /commitments     /reminders
      (GET)           │                │
      [no auth]       │                │
                      │                │
             ┌────────┼────────┐       │
             │        │        │       │
          /open    /close   /update    │
         (POST)   (POST)   (POST)     │
         (GET)                         │
             │                         │
          /query               ┌───────┼───────┐
          (GET)                │       │       │
                           /create   /due  /dispatch_due
                           (POST)   (GET)    (POST)
```

## 7. Module Dependency Graph

```
main.py
  ├── db.py (get_db, session management)
  ├── schemas.py (request/response models)
  └── services/
        ├── commitments.py
        │     └── models.py (Commitment, enums)
        └── reminders.py
              ├── models.py (Reminder)
              └── integrations/
                    └── whatsapp.py

worker.py
  ├── db.py (SessionLocal)
  └── services/reminders.py
        └── (same subtree as above)

models.py
  └── db.py (Base)

alembic/env.py
  ├── db.py (Base)
  └── models.py (registers models)
```
