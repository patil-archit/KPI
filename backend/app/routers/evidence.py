"""Read-only evidence + range API for the Cyber-Arena Tool Gateway.

This is the surface the Blue / Forensics / Critic agents are allowed to read.
It never exposes ground truth (which scenario ran, whether it was an attack).
Protected by a bearer token separate from the operator logins.
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from .. import settings
from ..db import get_db
from ..events import to_dict
from ..models import Event
from ..topology import topology

router = APIRouter(prefix="/evidence", tags=["evidence"])


def evidence_auth(x_evidence_token: str | None = Header(default=None)):
    if x_evidence_token != settings.EVIDENCE_TOKEN:
        raise HTTPException(401, "Invalid evidence token")
    return True


@router.get("/events")
def events(
    since_id: int = Query(default=0),
    source: str | None = None,
    host: str | None = None,
    event_type: str | None = None,
    purdue_level: int | None = None,
    limit: int = Query(default=500, le=2000),
    db: Session = Depends(get_db),
    _: bool = Depends(evidence_auth),
):
    q = db.query(Event).filter(Event.id > since_id)
    if source:
        q = q.filter(Event.source == source)
    if host:
        q = q.filter(Event.host == host)
    if event_type:
        q = q.filter(Event.event_type == event_type)
    if purdue_level is not None:
        q = q.filter(Event.purdue_level == purdue_level)
    rows = q.order_by(Event.id).limit(limit).all()
    return {"events": [to_dict(e) for e in rows], "count": len(rows),
            "last_id": rows[-1].id if rows else since_id}


@router.get("/sources")
def sources(db: Session = Depends(get_db), _: bool = Depends(evidence_auth)):
    from sqlalchemy import func
    rows = db.query(Event.source, func.count(Event.id)).group_by(Event.source).all()
    return {"sources": {s: n for s, n in rows}}


@router.get("/topology")
def get_topology(_: bool = Depends(evidence_auth)):
    return topology()


@router.get("/health")
def health(db: Session = Depends(get_db), _: bool = Depends(evidence_auth)):
    from ..plant.sim import plant
    s = plant.snapshot()
    return {"status": "running", "process": {k: round(s[k], 2) for k in ("temperature", "pressure", "level")},
            "sis_tripped": s["sis_tripped"], "event_count": db.query(Event).count()}
