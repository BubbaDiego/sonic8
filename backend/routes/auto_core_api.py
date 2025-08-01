from fastapi import APIRouter
from pydantic import BaseModel
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
