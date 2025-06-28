# ──────────────────────────────────────────────────────────────
# File: test_hedge_auto_wizard.py
# Author: BubbaDiego
# Created: 2025‑06‑24
# Description:
#   Tests Hedge Wizard integration and API endpoints.
# ──────────────────────────────────────────────────────────────
# tests/test_hedge_auto_wizard.py
from flask import Flask
import pytest
from unittest.mock import patch
import sys, os

# Ensure correct import paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hedge_core.hedge_wizard_bp import wizard_bp

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(wizard_bp, url_prefix="/sonic_labs/api/wizard")
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@patch("hedge_core.hedge_wizard_bp.AutoHedgeWizardCore")
def test_wizard_suggest(mock_core, client):
    mock_core.return_value.suggest_liq_distance.return_value = {
        "side": "long",
        "updates": {"collateral": 250},
        "note": "increase long LD"
    }
    response = client.get("/sonic_labs/api/wizard/suggest?hedge_id=123&price=100&mode=liq_dist&target=15")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["order_definition"]["updates"]["collateral"] == 250
    assert json_data["metrics"]["mode"] == "liq_dist"

@patch("hedge_core.hedge_wizard_bp.AutoHedgeWizardCore")
def test_wizard_execute(mock_core, client):
    mock_core.return_value.execute_order.return_value = {
        "status": "queued",
        "order_id": "order-123"
    }
    response = client.post("/sonic_labs/api/wizard/execute", json={"side": "long", "updates": {"collateral": 250}})
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "queued"
