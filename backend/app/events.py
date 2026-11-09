"""Evidence emitter. Every component logs through here using one schema."""
import contextvars
import threading

from .db import session_scope
from .models import Event
from .topology import BY_HOST

_write_lock = threading.Lock()

# The scenario engine sets this to a list; every event emitted inside the
# scenario's context is recorded for ground truth. Nothing about it is stored
# on the event itself, so agents cannot tell scenario events from organic ones.
capture: contextvars.ContextVar[list | None] = contextvars.ContextVar("capture", default=None)


def emit(
    *,
    source: str,
    host: str,
    event_type: str,
    change_type: str = "none",
    actor: str | None = None,
    src_ip: str | None = None,
    dst_ip: str | None = None,
    protocol: str | None = None,
    outcome: str = "success",
    severity: str = "info",
    purdue_level: int | None = None,
    **detail,
) -> int:
    if purdue_level is None:
        purdue_level = BY_HOST.get(host, {}).get("level", 5)
    if dst_ip is None and host in BY_HOST:
        dst_ip = BY_HOST[host]["ip"]
    with _write_lock, session_scope() as s:
        ev = Event(
            source=source, host=host, purdue_level=purdue_level, event_type=event_type,
            change_type=change_type, actor=actor, src_ip=src_ip, dst_ip=dst_ip,
            protocol=protocol, outcome=outcome, severity=severity, detail=detail,
        )
        s.add(ev)
        s.flush()
        eid = ev.id
    cap = capture.get()
    if cap is not None:
        cap.append(eid)
    return eid


def to_dict(e: Event) -> dict:
    return {
        "id": e.id, "ts": e.ts.isoformat() if e.ts else None, "source": e.source, "host": e.host,
        "purdue_level": e.purdue_level, "event_type": e.event_type, "change_type": e.change_type,
        "actor": e.actor, "src_ip": e.src_ip, "dst_ip": e.dst_ip, "protocol": e.protocol,
        "outcome": e.outcome, "severity": e.severity, "detail": e.detail or {},
    }
