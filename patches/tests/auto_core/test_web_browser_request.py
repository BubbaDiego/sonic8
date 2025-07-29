import pytest
from backend.core.auto_core import AutoCore, WebBrowserRequest

@pytest.mark.asyncio
async def test_web_browser_request():
    core = AutoCore()
    result = await core.run(WebBrowserRequest("https://example.org"))
    assert "Example Domain" in result["title"]
