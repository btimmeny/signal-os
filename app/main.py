"""FastAPI application — commitment log REST API."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    CommentCreateRequest,
    CommentResponse,
    CommitmentCloseRequest,
    CommitmentOpenRequest,
    CommitmentResponse,
    CommitmentSetPriorityRequest,
    CommitmentUpdateRequest,
    ObjectiveCreateRequest,
    ObjectiveLinkRequest,
    ObjectiveLinkResponse,
    ObjectiveResponse,
    ObjectiveUpdateCreateRequest,
    ObjectiveUpdateRequest,
    ObjectiveUpdateResponse,
    ReminderCreateRequest,
    ReminderResponse,
    StatusDataRequest,
    StatusReportCreateRequest,
    StatusReportResponse,
)
from app.services import comments as comment_svc
from app.services import commitments as commitment_svc
from app.services import objective_links as link_svc
from app.services import objective_updates as obj_update_svc
from app.services import objectives as objective_svc
from app.services import reminders as reminder_svc
from app.services import status_reports as report_svc

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
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {"ok": db_ok, "db": "connected" if db_ok else "unreachable"}


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
        priority_order=body.priority_order,
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
# Priority ordering
# ---------------------------------------------------------------------------

@app.post("/commitments/set_priority", response_model=CommitmentResponse)
def commitments_set_priority(body: CommitmentSetPriorityRequest, db: Session = Depends(get_db)):
    c = commitment_svc.set_priority(
        db,
        commitment_id=body.commitment_id,
        priority_order=body.priority_order,
    )
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return CommitmentResponse.from_orm_with_days(c)


@app.get("/commitments/priorities", response_model=list[CommitmentResponse])
def commitments_priorities(db: Session = Depends(get_db)):
    rows = commitment_svc.list_priorities(db)
    return [CommitmentResponse.from_orm_with_days(c) for c in rows]


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

@app.post("/commitments/comment", response_model=CommentResponse)
def commitments_add_comment(body: CommentCreateRequest, db: Session = Depends(get_db)):
    comment = comment_svc.add_comment(
        db,
        commitment_id=body.commitment_id,
        body=body.body,
        author=body.author,
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return CommentResponse.from_orm_row(comment)


@app.get("/commitments/comments", response_model=list[CommentResponse])
def commitments_list_comments(
    commitment_id: str = Query(...),
    db: Session = Depends(get_db),
):
    comments = comment_svc.list_comments(db, commitment_id=commitment_id)
    if comments is None:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return [CommentResponse.from_orm_row(c) for c in comments]


# ---------------------------------------------------------------------------
# Strategic Objectives
# ---------------------------------------------------------------------------

@app.post("/objectives/create", response_model=ObjectiveResponse)
def objectives_create(body: ObjectiveCreateRequest, db: Session = Depends(get_db)):
    obj = objective_svc.create_objective(
        db,
        title=body.title,
        description=body.description,
        year=body.year,
        status=body.status.value,
    )
    return ObjectiveResponse.from_orm_row(obj)


@app.post("/objectives/update", response_model=ObjectiveResponse)
def objectives_update(body: ObjectiveUpdateRequest, db: Session = Depends(get_db)):
    fields = body.model_dump(exclude={"objective_id"}, exclude_none=True)
    if "status" in fields and hasattr(fields["status"], "value"):
        fields["status"] = fields["status"].value
    obj = objective_svc.update_objective(db, objective_id=body.objective_id, **fields)
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")
    return ObjectiveResponse.from_orm_row(obj)


@app.get("/objectives/list", response_model=list[ObjectiveResponse])
def objectives_list(
    db: Session = Depends(get_db),
    year: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
):
    rows = objective_svc.list_objectives(db, year=year, status=status)
    return [ObjectiveResponse.from_orm_row(o) for o in rows]


@app.get("/objectives/get", response_model=ObjectiveResponse)
def objectives_get(
    objective_id: str = Query(...),
    db: Session = Depends(get_db),
):
    obj = objective_svc.get_objective(db, objective_id=objective_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")
    return ObjectiveResponse.from_orm_row(obj)


# ---------------------------------------------------------------------------
# Objective-Commitment Links
# ---------------------------------------------------------------------------

@app.post("/objectives/link", response_model=ObjectiveLinkResponse)
def objectives_link(body: ObjectiveLinkRequest, db: Session = Depends(get_db)):
    link = link_svc.link_commitment(
        db,
        objective_id=body.objective_id,
        commitment_id=body.commitment_id,
        rationale=body.rationale,
    )
    if not link:
        raise HTTPException(status_code=404, detail="Objective or commitment not found")
    return ObjectiveLinkResponse.from_orm_row(link)


@app.post("/objectives/unlink")
def objectives_unlink(body: ObjectiveLinkRequest, db: Session = Depends(get_db)):
    removed = link_svc.unlink_commitment(
        db,
        objective_id=body.objective_id,
        commitment_id=body.commitment_id,
    )
    if not removed:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"detail": "Link removed"}


@app.get("/objectives/links", response_model=list[ObjectiveLinkResponse])
def objectives_links(
    objective_id: str = Query(...),
    db: Session = Depends(get_db),
):
    links = link_svc.list_links_for_objective(db, objective_id=objective_id)
    if links is None:
        raise HTTPException(status_code=404, detail="Objective not found")
    return [ObjectiveLinkResponse.from_orm_row(l) for l in links]


@app.get("/commitments/objectives", response_model=list[ObjectiveLinkResponse])
def commitments_objectives(
    commitment_id: str = Query(...),
    db: Session = Depends(get_db),
):
    links = link_svc.list_links_for_commitment(db, commitment_id=commitment_id)
    if links is None:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return [ObjectiveLinkResponse.from_orm_row(l) for l in links]


# ---------------------------------------------------------------------------
# Objective Updates
# ---------------------------------------------------------------------------

@app.post("/objectives/update_note", response_model=ObjectiveUpdateResponse)
def objectives_add_update(body: ObjectiveUpdateCreateRequest, db: Session = Depends(get_db)):
    update = obj_update_svc.add_update(
        db,
        objective_id=body.objective_id,
        body=body.body,
        author=body.author,
    )
    if not update:
        raise HTTPException(status_code=404, detail="Objective not found")
    return ObjectiveUpdateResponse.from_orm_row(update)


@app.get("/objectives/updates", response_model=list[ObjectiveUpdateResponse])
def objectives_list_updates(
    objective_id: str = Query(...),
    db: Session = Depends(get_db),
):
    updates = obj_update_svc.list_updates(db, objective_id=objective_id)
    if updates is None:
        raise HTTPException(status_code=404, detail="Objective not found")
    return [ObjectiveUpdateResponse.from_orm_row(u) for u in updates]


# ---------------------------------------------------------------------------
# Status Reports
# ---------------------------------------------------------------------------

@app.post("/status/report", response_model=StatusReportResponse)
def status_create_report(body: StatusReportCreateRequest, db: Session = Depends(get_db)):
    report = report_svc.create_report(
        db,
        period_type=body.period_type.value,
        period_start=body.period_start,
        period_end=body.period_end,
        body=body.body,
    )
    return StatusReportResponse.from_orm_row(report)


@app.get("/status/reports", response_model=list[StatusReportResponse])
def status_list_reports(
    period_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return [StatusReportResponse.from_orm_row(r) for r in report_svc.list_reports(db, period_type=period_type)]


@app.get("/status/report")
def status_get_report(
    report_id: str = Query(...),
    db: Session = Depends(get_db),
):
    report = report_svc.get_report(db, report_id=report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return StatusReportResponse.from_orm_row(report)


@app.post("/status/data")
def status_gather_data(body: StatusDataRequest, db: Session = Depends(get_db)):
    data = report_svc.gather_status_data(
        db,
        period_start=body.period_start,
        period_end=body.period_end,
    )
    return data


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
