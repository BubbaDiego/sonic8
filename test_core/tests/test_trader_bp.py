import types
import pytest

from flask import Flask

from trader_core.trader_bp import trader_bp
import trader_core


class DummyWallets:
    def get_wallets(self):
        return [{"name": "TestWallet", "balance": 5.0}]

    def get_wallet_by_name(self, name):
        return {"name": name, "balance": 1.23}

    def read_wallets(self):
        return self.get_wallets()


class DummyTraders:
    """Minimal traders manager stub."""
    def __init__(self):
        self._traders = []
        self.created_data = None

    def list_traders(self):
        return list(self._traders)

    def get_trader_by_name(self, name):
        for t in self._traders:
            if t.get("name") == name:
                return t
        return None

    def create_trader(self, data):
        self.created_data = data
        self._traders.append(data)
        return True

    def delete_trader(self, name):
        return False

    def delete_all_traders(self):
        self._traders = []

    def export_to_json(self, path=None):
        import json
        from data import dl_traders as dl_t
        if path is None:
            path = dl_t.ACTIVE_TRADERS_JSON_PATH
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self._traders, fh)

    def import_from_json(self, path=None):
        import json, os
        from data import dl_traders as dl_t
        if path is None:
            path = dl_t.ACTIVE_TRADERS_JSON_PATH
        if not os.path.exists(path):
            return 0
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            self._traders = data
            return len(data)
        return 0


class DummyLocker:
    def __init__(self):
        self.wallets = DummyWallets()
        self.traders = DummyTraders()
        self.positions = types.SimpleNamespace(get_all_positions=lambda: [])
        self.portfolio = types.SimpleNamespace(get_latest_snapshot=lambda: {})

    def get_last_update_times(self):
        return {}

    def read_wallets(self):
        return self.wallets.get_wallets()

    def get_wallet_by_name(self, name):
        return self.wallets.get_wallet_by_name(name)


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.data_locker = DummyLocker()
    # Preload a trader for API tests
    app.data_locker.traders._traders.append(
        {
            "name": "Angie",
            "born_on": "2020-01-01T00:00:00",
            "initial_collateral": 0.0,
        }
    )
    app.register_blueprint(trader_bp)
    # Map explicit route for our dummy client
    func = app.routes.get("/trader/api/traders/<name>", {}).get("GET")
    if func:
        app.routes["/trader/api/Angie"] = {"GET": lambda: func(name="Angie")["trader"]}
    del_func = app.routes.get("/trader/api/traders/<name>/delete", {}).get("DELETE")
    if del_func:
        app.routes["/trader/api/traders/Angie/delete"] = {"DELETE": lambda: del_func(name="Angie")}
        app.routes["/trader/api/traders/Ghost/delete"] = {"DELETE": lambda: del_func(name="Ghost")}
    fac_func = app.routes.get("/trader/factory/<name>", {}).get("GET")
    if fac_func:
        app.routes["/trader/factory/Angie"] = {"GET": lambda: fac_func(name="Angie")}
    profile_func = app.routes.get("/trader/profile/<name>", {}).get("GET")
    if profile_func:
        from importlib import import_module
        import os
        import json
        import re

        DummyResponse = import_module("conftest").DummyResponse

        class ProfileResp(DummyResponse):
            def get_data(self, as_text=False):
                return self.data.decode() if as_text else self.data

        def profile_page():
            template_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "shared",
                "incoming",
                "templates",
                "trader",
                "trader_profile.html",
            )
            html = open(template_path, "r", encoding="utf-8").read()
            trader = app.data_locker.traders.get_trader_by_name("Angie")
            html = html.replace("{{ trader | tojson }}", json.dumps(trader))
            html = re.sub(r"{%.*?%}", "", html)
            return ProfileResp(html)

        app.routes["/trader/profile/Angie"] = {"GET": profile_page}
    color_func = app.routes.get("/trader/api/persona_colors/<name>", {}).get("POST")
    if color_func:
        app.routes["/trader/api/persona_colors/Yoda"] = {"POST": lambda: color_func(name="Yoda")}
    with app.test_client() as client:
        yield client


def test_trader_api(client):
    resp = client.get("/trader/api/Angie")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["name"] == "Angie"
    assert "born_on" in data and "initial_collateral" in data
    from datetime import datetime
    datetime.fromisoformat(data["born_on"])


def test_trader_factory_page(client):
    resp = client.get("/trader/factory/Angie")
    assert resp.status_code == 200
    assert b"Angie" in resp.data


def test_trader_cards_page(client):
    resp = client.get("/trader/cards")
    assert resp.status_code == 200
    # Should include at least one persona name
    assert b"Angie" in resp.data


def test_wallet_list_api(client):
    resp = client.get("/trader/api/wallets")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert isinstance(data["wallets"], list)


def test_delete_missing_trader_returns_error(client):
    resp = client.delete("/trader/api/traders/Ghost/delete")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["success"] is False


def test_list_traders_handles_missing_persona(client):
    client.application.data_locker.traders._traders = [
        {
            "name": "Ghost",
            "born_on": "2020-01-01T00:00:00",
            "initial_collateral": 0.0,
        }
    ]
    resp = client.get("/trader/api/traders")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["traders"][0]["name"] == "Ghost"
    assert "wallet_balance" in data["traders"][0]
    assert "born_on" in data["traders"][0]
    assert "initial_collateral" in data["traders"][0]
    from datetime import datetime
    datetime.fromisoformat(data["traders"][0]["born_on"])


def test_list_traders_triggers_wallet_refresh(client):
    called = {}

    def refresh():
        called["r"] = True

    client.application.system_core = types.SimpleNamespace(
        wallet_core=types.SimpleNamespace(refresh_wallet_balances=refresh)
    )
    resp = client.get("/trader/api/traders")
    assert resp.status_code == 200
    assert called.get("r") is True


def test_list_traders_returns_json(client):
    client.application.data_locker.traders._traders = []
    resp = client.get("/trader/api/traders")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert isinstance(data.get("traders"), list)


def test_create_trader_sets_born_on_and_collateral(client):
    resp = client.post(
        "/trader/api/traders/create",
        json={"name": "Bob", "wallet": "TestWallet"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    created = client.application.data_locker.traders.created_data
    assert created.get("born_on")
    assert created.get("initial_collateral") == 1.23


def test_create_trader_failure_returns_error(client):
    def fail(_data):
        raise RuntimeError("db error")

    client.application.data_locker.traders.create_trader = fail
    resp = client.post(
        "/trader/api/traders/create",
        json={"name": "Bad"},
    )
    assert resp.status_code == 500
    data = resp.get_json()
    assert data["success"] is False


def test_create_star_wars_traders(client):
    resp = client.post("/trader/api/traders/create_star_wars")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    names = {t["name"] for t in client.application.data_locker.traders._traders}
    assert "Yoda" in names
    assert "Leia" in names


def test_delete_all_traders(client):
    client.application.data_locker.traders._traders = [
        {"name": "A"},
        {"name": "B"},
    ]
    resp = client.post("/trader/api/traders/delete_all")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert client.application.data_locker.traders._traders == []


def test_persona_color_endpoints(client, monkeypatch, tmp_path):
    import json
    persona_dir = tmp_path / "personas"
    persona_dir.mkdir()
    (persona_dir / "Yoda.json").write_text(json.dumps({"name": "Yoda", "color": "#00ff00"}))
    monkeypatch.setattr(trader_core.trader_bp, "PERSONA_DIR", str(persona_dir))
    monkeypatch.setattr(trader_core.trader_bp, "STAR_WARS_PERSONAS", ["Yoda"])

    resp = client.get("/trader/api/persona_colors")
    assert resp.status_code == 200
    assert resp.get_json()["Yoda"] == "#00ff00"

    resp = client.post("/trader/api/persona_colors/Yoda", json={"color": "#ff0000"})
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True
    with open(persona_dir / "Yoda.json", "r") as fh:
        data = json.load(fh)
    assert data["color"] == "#ff0000"


def test_export_and_import_traders(client, tmp_path, monkeypatch):
    import json
    from data import dl_traders as dl_t

    json_path = tmp_path / "active_traders.json"
    monkeypatch.setattr(dl_t, "ACTIVE_TRADERS_JSON_PATH", json_path)

    resp = client.post("/trader/api/traders/export")
    assert resp.status_code == 200
    assert json_path.exists()

    client.application.data_locker.traders._traders = []
    resp = client.post("/trader/api/traders/import")
    assert resp.status_code == 200
    assert client.application.data_locker.traders._traders != []


def test_import_traders_from_uploaded_file(client):
    import json

    payload = [{"name": "UploadTest"}]
    resp = client.post("/trader/api/traders/import", json=payload)
    assert resp.status_code == 200
    assert any(t.get("name") == "UploadTest" for t in client.application.data_locker.traders._traders)


def test_quick_import_traders(client, monkeypatch):
    monkeypatch.setattr(
        client.application.data_locker.wallets,
        "get_wallets",
        lambda: [{"name": "VaderVault", "balance": 2.0, "is_active": True}],
    )
    resp = client.post("/trader/api/traders/quick_import")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert any(t.get("name") == "Vader" for t in client.application.data_locker.traders._traders)




def test_trader_profile_init_json(client):
    resp = client.get("/trader/profile/Angie")
    assert resp.status_code == 200
    assert "INIT_TRADER" in resp.get_data(as_text=True)
