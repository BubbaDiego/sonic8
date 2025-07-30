from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.core.auto_core import AutoCore
from backend.core.auto_core.requests.web_browser import WebBrowserRequest
from backend.core.logging import log

router = APIRouter(prefix="/api/auto-core", tags=["auto_core"])


class BrowserOpenRequest(BaseModel):
    url: str | None = None


@router.post("/open-browser")
async def open_browser(req: BrowserOpenRequest):
    """Launch a Chromium instance via AutoCore and return the page info."""
    core = AutoCore()
    try:
        result = await core.run(WebBrowserRequest(url=req.url or "https://example.org"))
        return result
    except Exception as e:
        log.error(f"open_browser failed: {e}", source="auto_core_api")
        raise HTTPException(status_code=500, detail=str(e))

__all__ = ["router"]
