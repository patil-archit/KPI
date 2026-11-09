"""Level 2/1/0: HMI (SCADA) and the OPC-UA style tag gateway, plus live state."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from .. import auth, flags
from ..alarms import ack as ack_alarm
from ..auth import Ctx
from ..db import get_db
from ..events import emit
from ..models import Alarm, TagSample
from ..plant.sim import ENGINEERING_LIMITS, RANGES, plant
from ..topology import ip_of

router = APIRouter(prefix="/api", tags=["plant"])

TAG_META = {
    "temperature": {"label": "Tank Temperature", "tag": "TT101"},
    "pressure": {"label": "Tank Pressure", "tag": "PT101"},
    "level": {"label": "Tank Level", "tag": "LT101"},
    "conveyor_speed": {"label": "Conveyor Speed", "tag": "SC201"},
    "motor_current": {"label": "Motor Current", "tag": "MC201"},
}


@router.get("/plant/state")
def state(db: Session = Depends(get_db), c: Ctx = Depends(auth.current)):
    s = plant.snapshot()
    tags = []
    for key, meta in TAG_META.items():
        r = RANGES[key]
        tags.append({"key": key, "tag": meta["tag"], "label": meta["label"], "unit": r["unit"],
                     "value": round(plant.reported_value(key), 2), "state": plant.tag_state.get(key, "normal"),
                     "normal": r["normal"], "alarm_hi": r.get("alarm_hi"), "trip_hi": r.get("trip_hi")})
    alarms = db.query(Alarm).filter(Alarm.active.is_(True)).order_by(desc(Alarm.ts)).all()
    return {
        "tags": tags,
        "setpoints": {"temp_sp": round(s["temp_sp"], 1), "conveyor_sp": round(s["conveyor_sp"], 2),
                      "pump_speed_sp": round(s["pump_speed_sp"], 0), "auto_mode": bool(s["auto_mode"])},
        "actuators": {"heater_enable": s["heater_enable"], "heater_out": round(s["heater_out"], 1),
                      "pump_run": s["pump_run"], "conveyor_run": s["conveyor_run"]},
        "production": {"bottles": s["bottles"], "rejects": s["rejects"]},
        "safety": {"sis_tripped": s["sis_tripped"], "sis_bypass": s["sis_bypass"],
                   "trip_temp_limit": s["trip_temp_limit"], "trip_pressure_limit": s["trip_pressure_limit"]},
        "program": {"version": s["program_version"], "sha256": s["program_sha"][:16]},
        "alarms": [{"id": a.id, "tag": a.tag, "level": a.level, "message": a.message,
                    "ts": a.ts.isoformat(), "acked_by": a.acked_by} for a in alarms],
        "limits": ENGINEERING_LIMITS,
        "speed": s["speed"],
    }


class SetpointIn(BaseModel):
    tag: str  # temp_sp | conveyor_sp | pump_speed_sp
    value: float


HR_ADDR = {"temp_sp": (0, 10.0), "conveyor_sp": (1, 100.0), "pump_speed_sp": (2, 1.0)}


@router.post("/hmi/setpoint")
def hmi_setpoint(body: SetpointIn, c: Ctx = Depends(auth.require("operator", "supervisor", "engineer", "admin"))):
    if body.tag not in HR_ADDR:
        raise HTTPException(400, "Unknown setpoint")
    addr, scale = HR_ADDR[body.tag]
    raw = int(round(body.value * scale)) & 0xFFFF
    ok, msg = plant.write(1, "hr", addr, [raw], {"src_ip": ip_of("hmi-01"), "actor": c.username,
                          "protocol": "modbus/tcp", "function_code": 6})
    if not ok:
        raise HTTPException(409, msg)
    return {"ok": True, "tag": body.tag, "value": body.value}


class CoilIn(BaseModel):
    coil: str  # heater_enable | pump_run | conveyor_run | alarm_reset
    on: bool


COIL_ADDR = {"heater_enable": 0, "pump_run": 1, "conveyor_run": 2, "alarm_reset": 3}


@router.post("/hmi/coil")
def hmi_coil(body: CoilIn, c: Ctx = Depends(auth.require("operator", "supervisor", "engineer", "admin"))):
    if body.coil not in COIL_ADDR:
        raise HTTPException(400, "Unknown coil")
    ok, msg = plant.write(1, "coil", COIL_ADDR[body.coil], [1 if body.on else 0],
                          {"src_ip": ip_of("hmi-01"), "actor": c.username, "protocol": "modbus/tcp", "function_code": 5})
    if not ok:
        raise HTTPException(409, msg)
    return {"ok": True}


@router.post("/hmi/alarms/{alarm_id}/ack")
def ack(alarm_id: int, c: Ctx = Depends(auth.require("operator", "supervisor", "engineer", "admin"))):
    if not ack_alarm(alarm_id, c.username, ip_of("hmi-01")):
        raise HTTPException(409, "Already acknowledged or not found")
    return {"ok": True}


@router.get("/historian/trend")
def trend(tag: str, minutes: int = 30, db: Session = Depends(get_db), c: Ctx = Depends(auth.current)):
    from datetime import timedelta
    from ..models import utcnow
    since = utcnow() - timedelta(minutes=minutes)
    rows = db.query(TagSample).filter(TagSample.tag == tag, TagSample.ts >= since).order_by(TagSample.ts).all()
    return {"tag": tag, "points": [{"ts": r.ts.isoformat(), "v": r.value} for r in rows]}
