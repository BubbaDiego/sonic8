import types
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.data.data_locker import DataLocker
import types, sys


# Stub out heavy dependencies before importing the router module
sys.modules.setdefault(
    "backend.core.cyclone_core.cyclone_engine", types.SimpleNamespace(Cyclone=object)
)

class _DummyRegistry:
    def get_all_monitors(self):
        return []

    def get(self, name):  # pragma: no cover - not used
        raise KeyError

sys.modules.setdefault(
    "backend.core.monitor_core.monitor_core",
    types.SimpleNamespace(MonitorCore=lambda: types.SimpleNamespace(registry=_DummyRegistry())),
)

import backend.routes.monitor_api_adapter as adapter
import backend.core.monitor_core.sonic_monitor as sm


def create_app():
    app = FastAPI()
    app.include_router(adapter.router)
    return app


def test_sonic_cycle_route(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))

    # Patch Cyclone and sonic_cycle to avoid heavy operations
    monkeypatch.setattr(adapter, "Cyclone", lambda: object())

    async def fake_cycle(loop_counter, cyclone):
        return None
    monkeypatch.setattr(adapter, "sonic_cycle", fake_cycle)

    client = TestClient(create_app())
    resp = client.post("/monitors/sonic_cycle")
    assert resp.status_code == 202
    assert resp.json()["status"] == "sonic cycle started"


