"""Background threads: the simulation tick, the historian sampler and noise bots."""
import random
import threading
import time

from . import settings
from .db import session_scope
from .events import emit
from .models import Alarm, ProductionOrder, TagSample, utcnow
from .plant.sim import RANGES, plant

_stop = threading.Event()
_threads: list[threading.Thread] = []


def _sim_loop():
    last = time.monotonic()
    while not _stop.is_set():
        now = time.monotonic()
        plant.tick(now - last)
        last = now
        _stop.wait(settings.SIM_TICK_SECONDS)


def _historian_loop():
    while not _stop.is_set():
        snap = plant.snapshot()
        with session_scope() as s:
            for tag in RANGES:
                s.add(TagSample(tag=tag, value=round(plant.reported_value(tag), 3)))
            s.add(TagSample(tag="bottles", value=snap["bottles"]))
            s.add(TagSample(tag="heater_out", value=round(snap["heater_out"], 2)))
            cutoff = utcnow().timestamp() - settings.HISTORIAN_RETENTION_HOURS * 3600
            old = s.query(TagSample).filter(TagSample.ts < utcnow().fromtimestamp(cutoff, tz=utcnow().tzinfo)).limit(500).all()
            for o in old:
                s.delete(o)
        emit(source="historian", host="historian-01", event_type="poll", protocol="modbus/tcp",
             src_ip="10.30.0.10", outcome="info", severity="info", tags=len(RANGES)) if random.random() < 0.02 else None
        _stop.wait(settings.HISTORIAN_INTERVAL)


def _noise_loop():
    """Simulated operators and planners doing routine work, so the agents' job is not trivial."""
    while not _stop.is_set():
        _stop.wait(random.uniform(20, 45))
        if _stop.is_set():
            break
        roll = random.random()
        try:
            if roll < 0.4:
                with session_scope() as s:
                    a = s.query(Alarm).filter(Alarm.active.is_(True), Alarm.acked_by.is_(None)).first()
                    if a:
                        a.acked_by = "p.nair"
                        a.acked_at = utcnow()
                        tag = a.tag
                        emit(source="hmi", host="hmi-01", event_type="alarm_ack", actor="p.nair",
                             src_ip="10.20.0.10", tag=tag)
            elif roll < 0.55:
                emit(source="auth", host="erp-01", event_type="login_success", actor="a.kulkarni",
                     src_ip="10.40.1.11", protocol="https", outcome="success", method="corp", note="routine")
            elif roll < 0.7:
                emit(source="historian", host="historian-01", event_type="report_view", actor="r.mehta",
                     src_ip="10.40.0.30", protocol="https", outcome="info")
            else:
                # tiny routine operator setpoint nudge within normal band, from the HMI
                from .plant.sim import ENGINEERING_LIMITS
                cur = plant.snapshot()["temp_sp"]
                new = round(min(78, max(68, cur + random.choice([-0.5, 0.5]))), 1)
                plant.write(1, "hr", 0, [int(new * 10)], {"src_ip": "10.20.0.10", "actor": "p.nair",
                            "protocol": "modbus/tcp", "function_code": 6})
        except Exception:
            pass


def start():
    if _threads:
        return
    _stop.clear()
    for fn in (_sim_loop, _historian_loop, _noise_loop):
        t = threading.Thread(target=fn, daemon=True, name=fn.__name__)
        t.start()
        _threads.append(t)


def stop():
    _stop.set()
    for t in _threads:
        t.join(timeout=2)
    _threads.clear()
