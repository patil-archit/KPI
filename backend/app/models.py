from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128))
    email: Mapped[str] = mapped_column(String(128), default="")
    department: Mapped[str] = mapped_column(String(64), default="")
    # admin | planner | supervisor | engineer | operator | maintenance | viewer | vendor
    role: Mapped[str] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(256))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    remote_access: Mapped[bool] = mapped_column(Boolean, default=False)
    breach_point: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    via: Mapped[str] = mapped_column(String(16))  # corp | remote | historian-local
    host: Mapped[str] = mapped_column(String(64))
    src_ip: Mapped[str] = mapped_column(String(64))
    mfa_pending: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Material(Base):
    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(32))
    uom: Mapped[str] = mapped_column(String(16))
    stock: Mapped[float] = mapped_column(Float)
    reorder_point: Mapped[float] = mapped_column(Float, default=0)
    location: Mapped[str] = mapped_column(String(32))


class ProductionOrder(Base):
    __tablename__ = "production_orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[str] = mapped_column(String(16), unique=True)
    material_code: Mapped[str] = mapped_column(String(32))
    product: Mapped[str] = mapped_column(String(128))
    quantity: Mapped[int] = mapped_column(Integer)
    completed_qty: Mapped[int] = mapped_column(Integer, default=0)
    # created | released | in_progress | completed | cancelled
    status: Mapped[str] = mapped_column(String(16), default="created")
    recipe_temp_sp: Mapped[float] = mapped_column(Float, default=72.0)
    recipe_conveyor_sp: Mapped[float] = mapped_column(Float, default=1.0)
    priority: Mapped[str] = mapped_column(String(16), default="normal")
    due_date: Mapped[str] = mapped_column(String(16), default="")
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MaintenanceNotification(Base):
    __tablename__ = "maintenance_notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[str] = mapped_column(String(16), unique=True)
    asset: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | in_process | closed
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WorkOrder(Base):
    __tablename__ = "work_orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[str] = mapped_column(String(16), unique=True)
    notification_number: Mapped[str | None] = mapped_column(String(16), nullable=True)
    asset: Mapped[str] = mapped_column(String(64))  # plc-01, sis-01, hmi-01 ...
    description: Mapped[str] = mapped_column(Text)
    change_type: Mapped[str] = mapped_column(String(32))  # logic | parameter | safety_interlock | none
    planned_change: Mapped[dict] = mapped_column(JSON, default=dict)
    # created | approved | in_progress | closed | rejected
    status: Mapped[str] = mapped_column(String(16), default="created")
    requested_by: Mapped[str] = mapped_column(String(64))
    assigned_to: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Event(Base):
    """The evidence record. Same schema for every source; never says whether it was a scenario."""
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    source: Mapped[str] = mapped_column(String(32))  # auth | network | plc | process | host | erp | historian | hmi | engineering
    host: Mapped[str] = mapped_column(String(64), index=True)
    purdue_level: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(48), index=True)
    change_type: Mapped[str] = mapped_column(String(24), default="none")
    actor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    src_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dst_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    protocol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    outcome: Mapped[str] = mapped_column(String(16), default="success")  # success | failure | blocked | info
    severity: Mapped[str] = mapped_column(String(16), default="info")  # info | low | moderate | high | critical
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class Flag(Base):
    __tablename__ = "flags"
    key: Mapped[str] = mapped_column(String(16), primary_key=True)
    mode: Mapped[str] = mapped_column(String(16))  # vulnerable | patched
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    share: Mapped[str] = mapped_column(String(32))  # corp | eng-ws
    folder: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(128))
    content: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(64))
    breach_point: Mapped[str | None] = mapped_column(String(16), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PlcProgram(Base):
    __tablename__ = "plc_programs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plc: Mapped[str] = mapped_column(String(32))
    version: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    author: Mapped[str] = mapped_column(String(64))
    comment: Mapped[str] = mapped_column(String(256), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TagSample(Base):
    __tablename__ = "tag_samples"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    tag: Mapped[str] = mapped_column(String(48), index=True)
    value: Mapped[float] = mapped_column(Float)


class Alarm(Base):
    __tablename__ = "alarms"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    tag: Mapped[str] = mapped_column(String(48))
    level: Mapped[str] = mapped_column(String(16))  # warning | high | trip
    message: Mapped[str] = mapped_column(String(256))
    value: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    acked_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Case(Base):
    """A scenario run. Ground truth lives here and is only served by the Developer Mode API."""
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_key: Mapped[str] = mapped_column(String(32), unique=True)
    scenario: Mapped[str] = mapped_column(String(32))
    variant: Mapped[str] = mapped_column(String(32), default="default")
    is_attack: Mapped[bool] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(String(16), default="running")  # running | finished | failed
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flags_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    ground_truth: Mapped[dict] = mapped_column(JSON, default=dict)
