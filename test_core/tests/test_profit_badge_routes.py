import pytest

from flask import Flask, render_template

from app.dashboard_bp import dashboard_bp
from flask import Blueprint
alerts_bp = Blueprint('alerts', __name__)

@alerts_bp.route('/status_page')
def _status_page():
    return render_template("alerts/alert_status.html", alerts=[])
from app.system_bp import system_bp
from dashboard import dashboard_service

@pytest.fixture
def client(monkeypatch):
    app = Flask(__name__)
    app.config["TESTING"] = True
    monkeypatch.setattr(dashboard_service, "get_profit_badge_value", lambda dl, sc: 42)
    import app.dashboard_bp as dashboard_module
    monkeypatch.setattr(dashboard_module, "get_dashboard_context", lambda dl, sc: {})

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(alerts_bp, url_prefix="/alerts")
    app.register_blueprint(system_bp, url_prefix="/system")

    # Simplify heavy view logic
    app.view_functions["system.hedge_calculator_page"] = lambda: render_template(
        "hedges/hedge_modifiers.html",
        theme={},
        long_positions=[],
        short_positions=[],
        modifiers={},
        default_long_id=None,
        default_short_id=None,
    )

    app.data_locker = object()
    app.system_core = object()

    @app.context_processor
    def inject_profit_badge():
        value = dashboard_service.get_profit_badge_value(app.data_locker, app.system_core)
        return {"profit_badge_value": value}

    with app.test_client() as client:
        yield client

def test_badge_on_new_dashboard(client):
    resp = client.get("/dash")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "profit-badge" in html
    assert "42" in html
    assert "dashboardContainer" in html

def test_badge_on_hedge_calculator(client):
    resp = client.get("/system/hedge_calculator")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "profit-badge" in html
    assert "42" in html

def test_badge_on_alert_status(client):
    resp = client.get("/alerts/status_page")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "profit-badge" in html
    assert "42" in html
