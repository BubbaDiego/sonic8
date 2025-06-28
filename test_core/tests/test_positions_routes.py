import types
import pytest
from flask import Flask
import app.positions_bp as positions_bp_module
from app.positions_bp import positions_bp
from tests.conftest import render_template as tmpl


class DummyLocker:
    def read_wallets(self):
        return []


class DummyPositionCore:
    def __init__(self, dl):
        self.dl = dl

    def get_active_positions(self):
        return [
            {
                "asset_type": "BTC",
                "wallet": "ObiVault",
                "travel_percent": 5.0,
                "pnl_after_fees_usd": 1.0,
                "collateral": 0,
                "value": 0,
                "size": 0,
                "leverage": 0,
                "stale": 1,
            }
        ]


class DummyCalcServices:
    def calculate_totals(self, positions):
        return types.SimpleNamespace(
            total_collateral=0,
            total_value=0,
            total_size=0,
            avg_leverage=0,
            avg_travel_percent=0,
        )


def _patched_render(name, **kw):
    if name == "liquidation_view.html":
        return tmpl("positions/liquidation_bars.html", **kw)
    return tmpl(f"positions/{name}", **kw)


@pytest.fixture
def client(monkeypatch):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.data_locker = DummyLocker()

    monkeypatch.setattr(positions_bp_module, "PositionCore", DummyPositionCore)
    monkeypatch.setattr(positions_bp_module, "CalcServices", DummyCalcServices)
    monkeypatch.setattr(positions_bp_module, "render_template", _patched_render)

    app.register_blueprint(positions_bp, url_prefix="/positions")

    with app.test_client() as client:
        yield client


def test_positions_center_page(client):
    resp = client.get("/positions/positions_center")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "horizontal-icon-toggle" in html
    assert "view-container" in html
    assert "data-view=\"positions\"" in html
    assert "data-view=\"liquidation\"" in html


def test_positions_snippet_routes(client):
    resp = client.get("/positions/positions_list")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "positionsTableContainer" in html
    assert "positions-table" in html

    resp = client.get("/positions/liquidation_view")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "Liquidation Bars" in html
    assert "liq-row" in html


def test_liquidation_view_stale_icon(client):
    resp = client.get("/positions/liquidation_view")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "fa-circle-question" in html
