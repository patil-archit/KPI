"""Developer Mode / Range Control Center API.

This is the one place that controls the range: breach-point switchboard, presets,
scenario launcher, ground-truth viewer, plant controls and reset. It is served on
a SEPARATE port and protected by its own token. The Cyber-Arena agents must never
be able to reach it, or the evaluation is meaningless.
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from .. import flags, scenarios, seed, settings
from ..auth import MFA_INBOX
from ..db import get_db
from ..models import Case, Event
from ..plant.sim import plant

router = APIRouter(prefix="/dev", tags=["developer-mode"])


def dev_auth(x_dev_token: str | None = Header(default=None)):
    if x_dev_token != settings.DEV_TOKEN:
        raise HTTPException(401, "Invalid developer token")
    return True


D = Depends(dev_auth)


@router.get("/breach-points")
def breach_points(_: bool = D):
    modes = flags.snapshot()
    return {"breach_points": [{**b, "mode": modes.get(b["key"], "vulnerable")} for b in flags.BREACH_POINTS],
            "presets": {k: {"label": v["label"], "description": v["description"]} for k, v in flags.PRESETS.items()}}


class FlagsIn(BaseModel):
    changes: dict[str, str]


@router.post("/breach-points")
def set_flags(body: FlagsIn, _: bool = D):
    try:
        return {"flags": flags.set_modes(body.changes)}
    except ValueError as e:
        raise HTTPException(400, str(e))


class PresetIn(BaseModel):
    preset: str


@router.post("/preset")
def apply_preset(body: PresetIn, _: bool = D):
    p = flags.PRESETS.get(body.preset)
    if not p:
        raise HTTPException(404, "Unknown preset")
    return {"flags": flags.set_modes(p["flags"]), "applied": body.preset}


@router.get("/scenarios")
def list_scenarios(_: bool = D):
    return {"scenarios": scenarios.catalogue(), "running": scenarios.status()}


class RunIn(BaseModel):
    key: str
    fast: bool = True
    actor: str = "attacker"


@router.post("/scenarios/run")
def run_scenario(body: RunIn, _: bool = D):
    try:
        return scenarios.run(body.key, fast=body.fast, actor=body.actor)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(409, str(e))


@router.get("/cases")
def cases(limit: int = 50, db: Session = Depends(get_db), _: bool = D):
    rows = db.query(Case).order_by(desc(Case.id)).limit(limit).all()
    return [{"case_key": c.case_key, "scenario": c.scenario, "variant": c.variant, "is_attack": c.is_attack,
             "status": c.status, "started_at": c.started_at.isoformat(),
             "first_event_id": c.first_event_id, "last_event_id": c.last_event_id,
             "techniques": c.ground_truth.get("techniques", [])} for c in rows]


@router.get("/cases/{case_key}")
def case_detail(case_key: str, db: Session = Depends(get_db), _: bool = D):
    c = db.query(Case).filter(Case.case_key == case_key).first()
    if not c:
        raise HTTPException(404, "Case not found")
    return {"case_key": c.case_key, "scenario": c.scenario, "variant": c.variant, "is_attack": c.is_attack,
            "flags_snapshot": c.flags_snapshot, "ground_truth": c.ground_truth,
            "started_at": c.started_at.isoformat(),
            "finished_at": c.finished_at.isoformat() if c.finished_at else None}


# --------------------------------------------------------------------- plant controls
class SpeedIn(BaseModel):
    speed: float


@router.post("/plant/speed")
def set_speed(body: SpeedIn, _: bool = D):
    plant.speed = max(0.0, min(20.0, body.speed))
    return {"speed": plant.speed}


class FaultIn(BaseModel):
    tag: str
    kind: str  # stuck | drift | clear
    value: float = 0.0


@router.post("/plant/fault")
def inject_fault(body: FaultIn, _: bool = D):
    if body.kind == "clear":
        plant.fault = None
    else:
        plant.fault = {"tag": body.tag, "kind": body.kind, "value": body.value}
    from ..events import emit
    emit(source="process", host="process", event_type="sensor_fault_injected" if body.kind != "clear" else "sensor_fault_cleared",
         outcome="info", severity="low", tag=body.tag, kind=body.kind, value=body.value)
    return {"fault": plant.fault}


@router.get("/mfa-inbox")
def mfa_inbox(_: bool = D):
    return {"messages": list(MFA_INBOX)}


@router.get("/status")
def dev_status(db: Session = Depends(get_db), _: bool = D):
    s = plant.snapshot()
    return {"flags": flags.snapshot(), "running_scenario": scenarios.status(), "speed": s["speed"],
            "event_count": db.query(Event).count(), "case_count": db.query(Case).count(),
            "process": {k: round(s[k], 2) for k in ("temperature", "pressure", "level")},
            "sis_tripped": s["sis_tripped"], "program_version": s["program_version"]}


@router.post("/reset")
def reset(_: bool = D):
    seed.reset_database()
    plant.reset()
    return {"ok": True, "message": "Range reset to baseline"}
