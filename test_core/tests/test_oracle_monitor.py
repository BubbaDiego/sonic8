import types
from flask import Flask
from pathlib import Path
import monitor.oracle_monitor.oracle_monitor as om
from monitor.oracle_monitor import oracle_monitor_config as cfg_mod
from monitor.oracle_monitor import credentials_manager as cred_mod
from monitor.oracle_monitor import oracle_monitor_api as api
from monitor.oracle_monitor import oracle_monitor_xcom as xcom_mod


class DummySystem:
    def __init__(self):
        self.vars = {}

    def get_var(self, key):
        return self.vars.get(key)

    def set_var(self, key, value):
        self.vars[key] = value


class DummyLocker:
    def __init__(self):
        self.system = DummySystem()
        self.db = object()


class DummyOracle:
    def __init__(self, _):
        self.asked = []

    def ask(self, topic, persona=None):
        self.asked.append((topic, persona))
        return f"reply-{topic}"


class DummyXCom:
    def __init__(self, _):
        self.sent = []

    def send_notification(self, *a, **k):
        self.sent.append((a, k))
        return {"ok": True}


# --- config functions ----------------------------------------------------

def test_load_save_config(monkeypatch):
    dl = DummyLocker()
    monkeypatch.setattr(cfg_mod, "DataLocker", lambda *_a, **_k: dl)

    cfg_mod.save_config({"a": 1})
    assert dl.system.get_var("oracle_monitor_config") == {"a": 1}
    assert cfg_mod.load_config() == {"a": 1}


# --- API endpoints -------------------------------------------------------

def _make_app(monkeypatch, dl, personas=None):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(api.oracle_monitor_api, url_prefix="/oracle")
    app.data_locker = dl
    monkeypatch.setattr(api, "load_config", lambda: {"persona": "p1", "topics": ["portfolio"]})
    monkeypatch.setattr(api, "save_config", lambda cfg: dl.system.set_var("saved", cfg))

    if personas is None:
        personas = ["p1", "p2"]
    monkeypatch.setattr(api, "PersonaManager", lambda: types.SimpleNamespace(list_personas=lambda: personas))
    monkeypatch.setattr(api, "render_template", lambda _t, personas=None, **_k: "<select id='persona'>" + "".join(f"<option value='{p}'>{p}</option>" for p in (personas or [])) + "</select>")

    return app


def test_config_get(monkeypatch):
    dl = DummyLocker()
    app = _make_app(monkeypatch, dl)
    with app.test_client() as client:
        resp = client.get("/oracle/config")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["config"] == {"persona": "p1", "topics": ["portfolio"]}
        assert data["personas"] == ["p1", "p2"]

        assert "portfolio" in data["topics"]




def test_config_post(monkeypatch):
    dl = DummyLocker()
    app = _make_app(monkeypatch, dl)
    with app.test_client() as client:
        resp = client.post("/oracle/config", json={"persona": "p2", "topics": ["system"]})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert dl.system.get_var("saved") == {"persona": "p2", "topics": ["system"]}


def test_oracle_ui_route(monkeypatch):
    dl = DummyLocker()
    app = _make_app(monkeypatch, dl, personas=["Connie", "Nina"])
    with app.test_client() as client:
        resp = client.get("/oracle/")
        assert resp.status_code == 200
        html = resp.data.decode()

        assert "<option value='Connie'>Connie</option>" in html
        assert "<option value='Nina'>Nina</option>" in html

        assert "Oracle Monitor UI" in html
        assert 'option value="p1" selected' in html
        assert 'value="portfolio" checked' in html



# --- Monitor cycle ------------------------------------------------------

def test_oracle_monitor_cycle(monkeypatch):
    dl = DummyLocker()
    monkeypatch.setattr(om, "DataLocker", lambda *_a, **_k: dl)
    monkeypatch.setattr(om, "OracleCore", DummyOracle)
    monkeypatch.setattr(om, "XComCore", DummyXCom)
    monkeypatch.setattr(om, "load_config", lambda: {"persona": "p1", "topics": ["portfolio", "system"]})
    monkeypatch.setattr(om, "send_notification", lambda msg: dl.system.set_var("note", msg))
    monkeypatch.setattr(om, "validate_credentials", lambda: {"success": True})

    monitor = om.OracleMonitor()
    result = monitor._do_work()
    assert result["success"] is True
    assert dl.system.get_var("note") is not None
    assert len(result["results"]) == 2
