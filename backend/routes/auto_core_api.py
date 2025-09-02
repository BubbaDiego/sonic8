from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from importlib import import_module
from typing import Any, Dict

from backend.core.auto_core import AutoCore, WebBrowserRequest

router = APIRouter(prefix="/api/auto-core", tags=["auto_core"])

class BrowserOpenRequest(BaseModel):
    url: str | None = None

@router.post("/open-browser")
async def open_browser(req: BrowserOpenRequest):
    """
    Launches Chromium with (optional) Solflare extension and returns page meta.
    """
    core = AutoCore()
    result = await core.run(WebBrowserRequest(url=req.url or "https://example.org"))
    return result


class AutoCoreRunRequest(BaseModel):
    request_type: str
    params: Dict[str, Any] | None = None


@router.post("/run-request")
async def run_request(req: AutoCoreRunRequest):
    core = AutoCore()
    try:
        mod = import_module("backend.core.auto_core.requests")
        cls = getattr(mod, req.request_type)
    except Exception:
        raise HTTPException(status_code=400, detail="unknown request_type")

    params = req.params or {}
    try:
        request_obj = cls(**params)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return await core.run(request_obj)
