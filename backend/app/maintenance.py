"""Maintenance-window lookups shared by PLC, SIS and engineering checks."""
from .db import session_scope
from .models import WorkOrder, utcnow


def active_window(asset: str, change_type: str | None = None) -> dict | None:
    now = utcnow()
    with session_scope() as s:
        q = s.query(WorkOrder).filter(
            WorkOrder.asset == asset,
            WorkOrder.status.in_(["approved", "in_progress"]),
        )
        for wo in q.all():
            ws, we = wo.window_start, wo.window_end
            if ws is None or we is None:
                continue
            if ws.tzinfo is None:
                from datetime import timezone
                ws, we = ws.replace(tzinfo=timezone.utc), we.replace(tzinfo=timezone.utc)
            if ws <= now <= we and (change_type is None or wo.change_type == change_type):
                return {"number": wo.number, "change_type": wo.change_type, "assigned_to": wo.assigned_to}
    return None
