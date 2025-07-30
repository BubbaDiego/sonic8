import pytest
from backend.core.auto_core import AutoCore, WebBrowserRequest

@pytest.mark.asyncio
async def test_web_browser_request():
    core = AutoCore()
    result = await core.run(WebBrowserRequest("https://example.org"))
    assert "Example Domain" in result["title"]


def test_open_browser_missing_browsers(monkeypatch):
    """API returns friendly error when Playwright browsers are not installed."""
    from fastapi.testclient import TestClient
    import backend.sonic_backend_app as app_module
    from backend.core.auto_core.playwright_helper import PlaywrightHelper

    async def boom(self):
        raise RuntimeError(
            "Playwright browsers not installed. Run 'playwright install' and retry."
        )

    monkeypatch.setattr(PlaywrightHelper, "__aenter__", boom)

    client = TestClient(app_module.app)
    resp = client.post("/api/auto-core/open-browser", json={"url": "https://example.org"})
    assert resp.status_code == 500
    assert "playwright install" in resp.json()["detail"].lower()
