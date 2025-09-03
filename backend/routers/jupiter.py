from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from subprocess import Popen
from pathlib import Path

router = APIRouter(prefix="/jupiter", tags=["jupiter"])


class OpenReq(BaseModel):
    walletId: str
    url: str | None = None
    headless: bool = False


@router.post("/open")
def open_jupiter(req: OpenReq):
    launcher = Path("auto_core/launcher/open_jupiter.py").resolve()
    if not launcher.exists():
        raise HTTPException(status_code=500, detail="Launcher not found.")

    # Spawn detached so the API returns immediately.
    cmd = [
        "python",
        str(launcher),
        "--wallet-id", req.walletId
    ]
    if req.url:
        cmd += ["--url", req.url]
    if req.headless:
        cmd += ["--headless"]

    try:
        Popen(cmd)
        return {"ok": True, "launched": req.walletId}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Launch failed: {e}")
