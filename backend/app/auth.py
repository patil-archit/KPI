"""Authentication, sessions and the simulated MFA device."""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import os
import random
import secrets
from collections import deque
from datetime import timedelta, timezone

from fastapi import Depends, Header, HTTPException, Request

from . import flags
from .db import session_scope
from .events import emit
from .models import AuthSession, User, utcnow
from .topology import EXTERNAL_IPS, ip_of

# Where each role normally sits when it logs in from inside the plant.
ROLE_WORKSTATION = {
    "planner": "corp-ws-01", "admin": "corp-ws-01", "viewer": "corp-ws-01",
    "maintenance": "corp-ws-02", "supervisor": "corp-ws-02",
    "engineer": "eng-ws-01", "vendor": "eng-ws-01",
    "operator": "hmi-01",
}

# Simulated phone: one-time codes "sent" to users. Shown in Developer Mode.
MFA_INBOX: deque = deque(maxlen=50)


def hash_password(pw: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 60_000)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$")
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt_hex), 60_000)
    return hmac.compare_digest(dk.hex(), dk_hex)


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    return ip


def external_ip_for(username: str, real_ip: str) -> str:
    """Remote logins come 'from the internet'. If the real client is on a private
    or loopback address (the usual case in the lab) map it to a stable documentation
    address so evidence looks like an external origin."""
    try:
        if ipaddress.ip_address(real_ip).is_global:
            return real_ip
    except ValueError:
        pass
    return EXTERNAL_IPS[sum(map(ord, username)) % len(EXTERNAL_IPS)]


def _session_timeout() -> timedelta | None:
    return None if flags.vulnerable("B10") else timedelta(minutes=15)


def login(username: str, password: str, via: str, real_ip: str, *, src_ip_override: str | None = None) -> dict:
    """via: corp (ERP SSO), remote (vendor portal), historian-local."""
    target = {"corp": "erp-01", "remote": "portal-01", "historian-local": "historian-01"}[via]
    with session_scope() as s:
        user = s.query(User).filter(User.username == username).first()
        role = user.role if user else None
        if src_ip_override:
            src_ip = src_ip_override
        elif via == "remote":
            src_ip = external_ip_for(username, real_ip)
        else:
            src_ip = ip_of(ROLE_WORKSTATION.get(role or "viewer", "corp-ws-01"))

        def fail(reason: str):
            emit(source="auth", host=target, event_type="login_failure", actor=username, src_ip=src_ip,
                 protocol="https", outcome="failure", severity="low", reason=reason, method=via)
            raise HTTPException(401, "Invalid credentials" if reason != "remote access not permitted" else reason)

        if user is None:
            fail("unknown user")
        if not user.enabled:
            fail("account disabled")
        if not verify_password(password, user.password_hash):
            fail("bad password")
        if via == "remote" and not user.remote_access:
            fail("remote access not permitted")

        token = secrets.token_hex(24)
        mfa_needed = via == "remote" and not flags.vulnerable("B1")
        code = f"{random.randint(0, 999999):06d}" if mfa_needed else None
        host = "eng-ws-01" if via == "remote" else ("historian-01" if via == "historian-local" else ROLE_WORKSTATION.get(user.role, "corp-ws-01"))
        s.add(AuthSession(token=token, user_id=user.id, via=via, host=host, src_ip=src_ip,
                          mfa_pending=mfa_needed, mfa_code=code))
        if not mfa_needed:
            user.last_login = utcnow()
        info = {"username": user.username, "full_name": user.full_name, "role": user.role}

    if mfa_needed:
        MFA_INBOX.appendleft({"ts": utcnow().isoformat(), "username": username, "code": code})
        emit(source="auth", host=target, event_type="mfa_challenge", actor=username, src_ip=src_ip,
             protocol="https", outcome="info", method=via)
        return {"token": token, "mfa_required": True, "user": info}
    emit(source="auth", host=target, event_type="login_success", actor=username, src_ip=src_ip,
         protocol="https", outcome="success", method=via, session_host=host)
    if via == "remote":
        emit(source="host", host="eng-ws-01", event_type="remote_session_start", actor=username, src_ip=ip_of("portal-01"),
             protocol="rdp", outcome="success", origin_ip=src_ip)
    return {"token": token, "mfa_required": False, "user": info}


def verify_mfa(token: str, code: str) -> dict:
    with session_scope() as s:
        sess = s.get(AuthSession, token)
        if not sess or not sess.mfa_pending:
            raise HTTPException(400, "No pending MFA challenge")
        user = s.get(User, sess.user_id)
        if code.strip() != sess.mfa_code:
            emit(source="auth", host="portal-01", event_type="mfa_failure", actor=user.username, src_ip=sess.src_ip,
                 protocol="https", outcome="failure", severity="low")
            raise HTTPException(401, "Invalid code")
        sess.mfa_pending = False
        sess.mfa_code = None
        user.last_login = utcnow()
        src_ip, username = sess.src_ip, user.username
        info = {"username": user.username, "full_name": user.full_name, "role": user.role}
    emit(source="auth", host="portal-01", event_type="login_success", actor=username, src_ip=src_ip,
         protocol="https", outcome="success", method="remote", mfa=True, session_host="eng-ws-01")
    emit(source="host", host="eng-ws-01", event_type="remote_session_start", actor=username, src_ip=ip_of("portal-01"),
         protocol="rdp", outcome="success", origin_ip=src_ip)
    return {"token": token, "mfa_required": False, "user": info}


class Ctx:
    """The authenticated caller."""

    def __init__(self, user: User, sess: AuthSession):
        self.username = user.username
        self.full_name = user.full_name
        self.role = user.role
        self.user_id = user.id
        self.via = sess.via
        self.session_host = sess.host
        self.session_ip = sess.src_ip
        self.token = sess.token

    def ctx_from(self, host: str, **extra) -> dict:
        """Context for an action executed *from* a given plant host (e.g. hmi-01)."""
        return {"src_ip": ip_of(host), "actor": self.username, **extra}


def current(authorization: str | None = Header(default=None)) -> Ctx:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Not signed in")
    token = authorization.split(" ", 1)[1]
    with session_scope() as s:
        sess = s.get(AuthSession, token)
        if not sess or sess.mfa_pending:
            raise HTTPException(401, "Session expired")
        timeout = _session_timeout()
        last = sess.last_seen if sess.last_seen.tzinfo else sess.last_seen.replace(tzinfo=timezone.utc)
        if timeout and utcnow() - last > timeout:
            s.delete(sess)
            raise HTTPException(401, "Session expired")
        user = s.get(User, sess.user_id)
        if not user or not user.enabled:
            raise HTTPException(401, "Account disabled")
        sess.last_seen = utcnow()
        return Ctx(user, sess)


def require(*roles: str):
    def dep(c: Ctx = Depends(current)) -> Ctx:
        if c.role not in roles and c.role != "admin":
            raise HTTPException(403, f"Requires role: {', '.join(roles)}")
        return c
    return dep


def logout(token: str) -> None:
    with session_scope() as s:
        sess = s.get(AuthSession, token)
        if sess:
            s.delete(sess)
