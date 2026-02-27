"""FastAPI application — commitment log REST API."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    CommitmentCloseRequest,
    CommitmentOpenRequest,
    CommitmentResponse,
    CommitmentUpdateRequest,
    ReminderCreateRequest,
    ReminderResponse,
)
from app.services import commitments as commitment_svc
from app.services import reminders as reminder_svc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

AGENT_API_KEY = os.getenv("AGENT_API_KEY", "dev-key-change-me")

app = FastAPI(
    title="Signal OS",
    description="Personal commitment log system.",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
        return await call_next(request)

    key = request.headers.get("X-API-Key")
    if key != AGENT_API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})

    return await call_next(request)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"ok": True}


# ---------------------------------------------------------------------------
# Commitments
# ---------------------------------------------------------------------------

@app.post("/commitments/open", response_model=CommitmentResponse)
def commitments_open(body: CommitmentOpenRequest, db: Session = Depends(get_db)):
    c = commitment_svc.open_commitment(
        db,
        title=body.title,
        description=body.description,
        person=body.person,
        organization=body.organization,
        channel_type=body.channel_type.value if body.channel_type else None,
        channel_title=body.channel_title,
        channel_link=body.channel_link,
        urgency=body.urgency.value if body.urgency else None,
        due_at=body.due_at,
        source_snippet=body.source_snippet,
        status=body.status.value,
    )
    return CommitmentResponse.from_orm_with_days(c)


@app.post("/commitments/close")
def commitments_close(body: CommitmentCloseRequest, db: Session = Depends(get_db)):
    if not body.commitment_id and not body.title:
        raise HTTPException(status_code=400, detail="Provide commitment_id or title")

    closed, candidates = commitment_svc.close_commitment(
        db,
        commitment_id=body.commitment_id,
        title=body.title,
        person=body.person,
    )
    if closed:
        return CommitmentResponse.from_orm_with_days(closed)
    if candidates:
        return JSONResponse(
            status_code=409,
            content={
                "detail": "Multiple open commitments match. Specify commitment_id.",
                "candidates": [
                    CommitmentResponse.from_orm_with_days(c).model_dump(mode="json")
                    for c in candidates
                ],
            },
        )
    raise HTTPException(status_code=404, detail="No matching open commitment found")


@app.post("/commitments/update", response_model=CommitmentResponse)
def commitments_update(body: CommitmentUpdateRequest, db: Session = Depends(get_db)):
    fields = body.model_dump(exclude={"commitment_id"}, exclude_none=True)
    # Convert enum values to strings for the service layer
    for k in ("status", "urgency", "channel_type"):
        if k in fields and hasattr(fields[k], "value"):
            fields[k] = fields[k].value

    c = commitment_svc.update_commitment(db, commitment_id=body.commitment_id, **fields)
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return CommitmentResponse.from_orm_with_days(c)


@app.get("/commitments/open", response_model=list[CommitmentResponse])
def commitments_list_open(db: Session = Depends(get_db)):
    rows = commitment_svc.list_open(db)
    return [CommitmentResponse.from_orm_with_days(c) for c in rows]


@app.get("/commitments/query", response_model=list[CommitmentResponse])
def commitments_query(
    db: Session = Depends(get_db),
    person: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    urgency: Optional[str] = Query(None),
    channel_type: Optional[str] = Query(None),
    due_before: Optional[datetime] = Query(None),
    due_after: Optional[datetime] = Query(None),
    opened_before: Optional[datetime] = Query(None),
    opened_after: Optional[datetime] = Query(None),
    text: Optional[str] = Query(None),
):
    rows = commitment_svc.query_commitments(
        db,
        person=person,
        status=status,
        urgency=urgency,
        channel_type=channel_type,
        due_before=due_before,
        due_after=due_after,
        opened_before=opened_before,
        opened_after=opened_after,
        text=text,
    )
    return [CommitmentResponse.from_orm_with_days(c) for c in rows]


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------

@app.post("/reminders/create", response_model=ReminderResponse)
def reminders_create(body: ReminderCreateRequest, db: Session = Depends(get_db)):
    r = reminder_svc.create_reminder(
        db,
        commitment_id=body.commitment_id,
        remind_at=body.remind_at,
        message=body.message,
        delivery_target=body.delivery_target,
        delivery_channel=body.delivery_channel,
    )
    return ReminderResponse.from_orm_row(r)


@app.get("/reminders/due", response_model=list[ReminderResponse])
def reminders_due(db: Session = Depends(get_db)):
    rows = reminder_svc.get_due_reminders(db)
    return [ReminderResponse.from_orm_row(r) for r in rows]


@app.post("/reminders/dispatch_due", response_model=list[ReminderResponse])
def reminders_dispatch(db: Session = Depends(get_db)):
    dispatched = reminder_svc.dispatch_due_reminders(db)
    return [ReminderResponse.from_orm_row(r) for r in dispatched]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8300"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
