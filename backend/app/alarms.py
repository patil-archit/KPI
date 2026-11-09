from .db import session_scope
from .events import emit
from .models import Alarm, utcnow


def raise_alarm(tag: str, level: str, value: float, rng: dict) -> None:
    with session_scope() as s:
        exists = s.query(Alarm).filter(Alarm.tag == tag, Alarm.active.is_(True), Alarm.level == level).first()
        if exists:
            return
        limit = rng.get("trip_hi") if level == "trip" else rng.get("alarm_hi")
        s.add(Alarm(tag=tag, level=level, value=round(value, 3),
                    message=f"{tag.replace('_', ' ').title()} {'TRIP' if level == 'trip' else 'HIGH'} "
                            f"{value:.2f} {rng['unit']} (limit {limit})"))
    emit(source="hmi", host="hmi-01", event_type="alarm_raised", severity="moderate", outcome="info",
         tag=tag, level=level, value=round(value, 3))


def clear_alarm(tag: str) -> None:
    with session_scope() as s:
        for a in s.query(Alarm).filter(Alarm.tag == tag, Alarm.active.is_(True)).all():
            a.active = False
            a.cleared_at = utcnow()


def ack(alarm_id: int, user: str, src_ip: str) -> bool:
    with session_scope() as s:
        a = s.get(Alarm, alarm_id)
        if not a or a.acked_by:
            return False
        a.acked_by = user
        a.acked_at = utcnow()
        tag = a.tag
    emit(source="hmi", host="hmi-01", event_type="alarm_ack", actor=user, src_ip=src_ip, tag=tag, alarm_id=alarm_id)
    return True
