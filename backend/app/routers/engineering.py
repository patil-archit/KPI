"""Level 3: engineering workstation - file share, PLC project, logic download, remote portal."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import auth
from ..auth import Ctx
from ..db import get_db
from ..events import emit
from ..models import Document, PlcProgram, utcnow
from ..plant.sim import plant, sha256
from ..topology import ip_of

router = APIRouter(prefix="/api/eng", tags=["engineering"])


@router.get("/files")
def files(share: str = "corp", db: Session = Depends(get_db), c: Ctx = Depends(auth.current)):
    docs = db.query(Document).filter(Document.share == share).order_by(Document.folder, Document.name).all()
    return [{"id": d.id, "folder": d.folder, "name": d.name, "owner": d.owner,
             "updated_at": d.updated_at.isoformat()} for d in docs]


@router.get("/files/{doc_id}")
def read_file(doc_id: int, db: Session = Depends(get_db), c: Ctx = Depends(auth.current)):
    d = db.get(Document, doc_id)
    if not d or d.share == "archived":
        raise HTTPException(404, "Not found")
    emit(source="host", host="files-01" if d.share == "corp" else "eng-ws-01",
         event_type="file_read", actor=c.username, src_ip=c.session_ip, protocol="smb" if d.share == "corp" else "ssh",
         path=f"{d.folder}/{d.name}", share=d.share)
    return {"id": d.id, "folder": d.folder, "name": d.name, "owner": d.owner, "content": d.content}


@router.get("/program")
def get_program(c: Ctx = Depends(auth.require("engineer", "vendor", "admin"))):
    s = plant.snapshot()
    return {"source": plant.program_source, "sha256": s["program_sha"], "version": s["program_version"],
            "params": s["params"]}


class DownloadIn(BaseModel):
    source: str
    comment: str = ""
    from_host: str = "eng-ws-01"


@router.post("/program/download")
def download(body: DownloadIn, db: Session = Depends(get_db),
             c: Ctx = Depends(auth.require("engineer", "vendor", "admin"))):
    ctx = {"src_ip": ip_of(body.from_host), "actor": c.username, "comment": body.comment}
    ok, msg = plant.download_program(body.source, ctx)
    if not ok:
        raise HTTPException(409, msg)
    s = plant.snapshot()
    db.add(PlcProgram(plc="plc-01", version=s["program_version"], source=body.source,
                      sha256=s["program_sha"], author=c.username, comment=body.comment, active=True))
    for p in db.query(PlcProgram).filter(PlcProgram.plc == "plc-01").all():
        p.active = p.version == s["program_version"]
    db.commit()
    return {"ok": True, "message": msg, "version": s["program_version"], "sha256": s["program_sha"]}


@router.get("/program/versions")
def versions(db: Session = Depends(get_db), c: Ctx = Depends(auth.current)):
    rows = db.query(PlcProgram).filter(PlcProgram.plc == "plc-01").order_by(PlcProgram.version.desc()).all()
    return [{"version": p.version, "sha256": p.sha256, "author": p.author, "comment": p.comment,
             "active": p.active, "created_at": p.created_at.isoformat()} for p in rows]
