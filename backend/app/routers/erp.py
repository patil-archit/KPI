"""Level 4: ERP portal - production orders, inventory, plant maintenance, users."""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_, text

from .. import auth, flags
from ..auth import Ctx
from ..db import get_db
from ..events import emit
from ..models import (MaintenanceNotification, Material, ProductionOrder, User, WorkOrder, utcnow)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/erp", tags=["erp"])


def _order_dict(o: ProductionOrder) -> dict:
    return {"number": o.number, "material_code": o.material_code, "product": o.product,
            "quantity": o.quantity, "completed_qty": o.completed_qty, "status": o.status,
            "recipe": {"temp_sp": o.recipe_temp_sp, "conveyor_sp": o.recipe_conveyor_sp},
            "priority": o.priority, "due_date": o.due_date, "created_by": o.created_by,
            "created_at": o.created_at.isoformat()}


@router.get("/orders")
def orders(db: Session = Depends(get_db), c: Ctx = Depends(auth.current)):
    return [_order_dict(o) for o in db.query(ProductionOrder).order_by(ProductionOrder.number.desc()).all()]


class OrderIn(BaseModel):
    material_code: str
    quantity: int
    temp_sp: float = 72.0
    conveyor_sp: float = 1.0
    priority: str = "normal"
    due_days: int = 3


@router.post("/orders")
def create_order(body: OrderIn, db: Session = Depends(get_db),
                 c: Ctx = Depends(auth.require("planner", "admin"))):
    mat = db.query(Material).filter(Material.code == body.material_code).first()
    if not mat:
        raise HTTPException(404, "Unknown material")
    last = db.query(ProductionOrder).order_by(ProductionOrder.id.desc()).first()
    num = str(int(last.number) + 1) if last else "1000236"
    o = ProductionOrder(number=num, material_code=body.material_code, product=mat.name,
                        quantity=body.quantity, recipe_temp_sp=body.temp_sp, recipe_conveyor_sp=body.conveyor_sp,
                        priority=body.priority, created_by=c.username,
                        due_date=(utcnow() + timedelta(days=body.due_days)).date().isoformat())
    db.add(o)
    db.commit()
    emit(source="erp", host="erp-01", event_type="production_order_created", actor=c.username,
         src_ip=c.session_ip, protocol="https", number=num, material=body.material_code, quantity=body.quantity)
    return _order_dict(o)


@router.post("/orders/{number}/release")
def release_order(number: str, db: Session = Depends(get_db), c: Ctx = Depends(auth.require("planner", "supervisor", "admin"))):
    o = db.query(ProductionOrder).filter(ProductionOrder.number == number).first()
    if not o:
        raise HTTPException(404, "Order not found")
    o.status = "released"
    o.released_at = utcnow()
    db.commit()
    emit(source="erp", host="erp-01", event_type="production_order_released", actor=c.username,
         src_ip=c.session_ip, protocol="https", number=number)
    return _order_dict(o)


@router.get("/inventory")
def inventory(db: Session = Depends(get_db), c: Ctx = Depends(auth.current)):
    return [{"code": m.code, "name": m.name, "category": m.category, "uom": m.uom,
             "stock": m.stock, "reorder_point": m.reorder_point, "location": m.location,
             "below_reorder": m.stock < m.reorder_point}
            for m in db.query(Material).order_by(Material.code).all()]


# --------------------------------------------------------------------- user search (B2 surface)
@router.get("/users")
def users(q: str = Query(default=""), db: Session = Depends(get_db), c: Ctx = Depends(auth.current)):
    rows = db.query(User)
    if q:
        rows = rows.filter(or_(User.username.contains(q), User.full_name.contains(q), User.department.contains(q)))
    return [{"username": u.username, "full_name": u.full_name, "role": u.role,
             "department": u.department, "email": u.email, "enabled": u.enabled,
             "remote_access": u.remote_access, "last_login": u.last_login.isoformat() if u.last_login else None}
            for u in rows.order_by(User.username).all()]


# --------------------------------------------------------------------- plant maintenance
def _wo_dict(w: WorkOrder) -> dict:
    return {"number": w.number, "notification_number": w.notification_number, "asset": w.asset,
            "description": w.description, "change_type": w.change_type, "planned_change": w.planned_change,
            "status": w.status, "requested_by": w.requested_by, "assigned_to": w.assigned_to,
            "approved_by": w.approved_by,
            "window_start": w.window_start.isoformat() if w.window_start else None,
            "window_end": w.window_end.isoformat() if w.window_end else None,
            "created_at": w.created_at.isoformat()}


@router.get("/maintenance/notifications")
def notifications(db: Session = Depends(get_db), c: Ctx = Depends(auth.current)):
    return [{"number": n.number, "asset": n.asset, "description": n.description, "priority": n.priority,
             "status": n.status, "created_by": n.created_by, "created_at": n.created_at.isoformat()}
            for n in db.query(MaintenanceNotification).order_by(MaintenanceNotification.number.desc()).all()]


@router.get("/maintenance/work-orders")
def work_orders(db: Session = Depends(get_db), c: Ctx = Depends(auth.current)):
    return [_wo_dict(w) for w in db.query(WorkOrder).order_by(WorkOrder.number.desc()).all()]


class WorkOrderIn(BaseModel):
    asset: str
    description: str
    change_type: str = "parameter"  # logic | parameter | safety_interlock | none
    notification_number: str | None = None
    assigned_to: str | None = None
    window_start_in_minutes: int = 0
    window_minutes: int = 120
    planned_change: dict = {}


@router.post("/maintenance/work-orders")
def create_work_order(body: WorkOrderIn, db: Session = Depends(get_db),
                      c: Ctx = Depends(auth.require("maintenance", "supervisor", "engineer", "admin"))):
    last = db.query(WorkOrder).order_by(WorkOrder.id.desc()).first()
    num = str(int(last.number) + 1) if last else "80004412"
    w = WorkOrder(number=num, notification_number=body.notification_number, asset=body.asset,
                  description=body.description, change_type=body.change_type, planned_change=body.planned_change,
                  requested_by=c.username, assigned_to=body.assigned_to)
    db.add(w)
    db.commit()
    emit(source="erp", host="erp-01", event_type="work_order_created", actor=c.username, src_ip=c.session_ip,
         protocol="https", number=num, asset=body.asset, change_type=body.change_type)
    return _wo_dict(w)


class ApproveIn(BaseModel):
    window_start_in_minutes: int = 0
    window_minutes: int = 120


@router.post("/maintenance/work-orders/{number}/approve")
def approve_work_order(number: str, body: ApproveIn, db: Session = Depends(get_db), c: Ctx = Depends(auth.current)):
    w = db.query(WorkOrder).filter(WorkOrder.number == number).first()
    if not w:
        raise HTTPException(404, "Work order not found")
    # B4: proper rule is "a maintenance supervisor, not the requester, approves".
    proper = c.role in ("supervisor", "admin") and c.username != w.requested_by
    if not flags.vulnerable("B4") and not proper:
        emit(source="erp", host="erp-01", event_type="work_order_approval", actor=c.username, src_ip=c.session_ip,
             protocol="https", outcome="blocked", severity="moderate", number=number,
             reason="approver must be a supervisor other than the requester")
        raise HTTPException(403, "Approval requires a maintenance supervisor other than the requester")
    start = utcnow() + timedelta(minutes=body.window_start_in_minutes)
    w.status = "approved"
    w.approved_by = c.username
    w.window_start = start
    w.window_end = start + timedelta(minutes=body.window_minutes)
    db.commit()
    emit(source="erp", host="erp-01", event_type="work_order_approved", actor=c.username, src_ip=c.session_ip,
         protocol="https", outcome="success", severity="info", number=number, change_type=w.change_type,
         asset=w.asset, self_approved=(c.username == w.requested_by),
         window_start=w.window_start.isoformat(), window_end=w.window_end.isoformat())
    return _wo_dict(w)


@router.post("/maintenance/work-orders/{number}/close")
def close_work_order(number: str, db: Session = Depends(get_db), c: Ctx = Depends(auth.current)):
    w = db.query(WorkOrder).filter(WorkOrder.number == number).first()
    if not w:
        raise HTTPException(404, "Work order not found")
    w.status = "closed"
    w.closed_at = utcnow()
    db.commit()
    emit(source="erp", host="erp-01", event_type="work_order_closed", actor=c.username, src_ip=c.session_ip,
         protocol="https", number=number)
    return _wo_dict(w)
