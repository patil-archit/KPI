from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from .. import auth
from ..auth import Ctx

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str
    via: str = "corp"  # corp | remote | historian-local


class MfaIn(BaseModel):
    token: str
    code: str


@router.post("/login")
def login(body: LoginIn, request: Request):
    return auth.login(body.username, body.password, body.via, auth.client_ip(request))


@router.post("/mfa")
def mfa(body: MfaIn):
    return auth.verify_mfa(body.token, body.code)


@router.get("/me")
def me(c: Ctx = Depends(auth.current)):
    return {"username": c.username, "full_name": c.full_name, "role": c.role,
            "via": c.via, "session_host": c.session_host}


@router.post("/logout")
def logout(c: Ctx = Depends(auth.current)):
    auth.logout(c.token)
    return {"ok": True}
