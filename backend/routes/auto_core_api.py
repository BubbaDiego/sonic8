from fastapi import APIRouter
from pydantic import BaseModel
from backend.core.auto_core import AutoCore
from backend.core.auto_core.requests.web_browser import WebBrowserRequest

router = APIRouter(prefix="/api/auto-core", tags=["auto_core"])


class BrowserOpenRequest(BaseModel):
    url: str | None = None


@router.post("/open-browser")
async def open_browser(req: BrowserOpenRequest):
    """Launch a Chromium instance via AutoCore and return the page info."""
    core = AutoCore()
    result = await core.run(WebBrowserRequest(url=req.url or "https://example.org"))
    return result

__all__ = ["router"]
