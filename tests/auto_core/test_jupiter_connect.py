import json
import sys
import types
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

# Provide a minimal stub for the Playwright module so import works
playwright_module = types.ModuleType("playwright")
sync_api_module = types.ModuleType("playwright.sync_api")
def dummy_sync_playwright():
    class Dummy:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            pass
    return Dummy()
sync_api_module.sync_playwright = dummy_sync_playwright
playwright_module.sync_api = sync_api_module
sys.modules.setdefault("playwright", playwright_module)
sys.modules.setdefault("playwright.sync_api", sync_api_module)

from backend.routers import jupiter


def test_jupiter_connect(monkeypatch, tmp_path):
    app = FastAPI()
    app.include_router(jupiter.router, prefix="/api")
    app.add_api_route("/api/jupiter/connect", jupiter.connect_solfare, methods=["POST"])

    repo_root = tmp_path
    state_dir = repo_root / "auto_core" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "jupiter_cdp.json").write_text(json.dumps({"port": 9222}))
    monkeypatch.setattr(jupiter, "REPO_ROOT", repo_root)
    monkeypatch.setattr(jupiter, "STATE_DIR", state_dir)

    def fake_sync_playwright():
        raise HTTPException(status_code=500, detail={"ok": False, "code": "PLAYWRIGHT_FAIL", "detail": "stub"})
    monkeypatch.setattr(jupiter, "sync_playwright", fake_sync_playwright)

    client = TestClient(app)
    resp = client.post("/api/jupiter/connect")
    data = resp.json().get("detail", {})
    assert all(k in data for k in ("ok", "code", "detail"))
