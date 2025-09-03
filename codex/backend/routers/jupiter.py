from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from subprocess import Popen
from pathlib import Path
import sys

router = APIRouter(prefix="/jupiter", tags=["jupiter"])

class OpenReq(BaseModel):
    walletId: str
    url: str | None = None
    headless: bool = False

@router.post("/open")
def open_jupiter(req: OpenReq):
    launcher = Path("auto_core/launcher/open_jupiter.py").resolve()
    if not launcher.exists():
        raise HTTPException(status_code=500, detail="launcher not found")
    cmd = [sys.executable or "python", str(launcher), "--wallet-id", req.walletId]
    if req.url: cmd += ["--url", req.url]
    if req.headless: cmd += ["--headless"]
    Popen(cmd)
    return {"ok": True, "launched": req.walletId}
