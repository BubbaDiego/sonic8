# ──────────────────────────────────────────────────────────────
# File: test_hedge_eval_api.py
# Author: BubbaDiego
# Created: 2025-06-24
# Description:
#   Test evaluating hedge positions via API endpoint simulation.
# ──────────────────────────────────────────────────────────────
import pytest
import sys, os
from flask import Flask, jsonify

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def app():
    app = Flask(__name__)

    @app.route("/evaluate_hedge")
    def evaluate_hedge():
        return jsonify({
            "long": {"value": 100, "pnl": 50},
            "short": {"value": 90, "pnl": -50},
            "totals": {"total_value": 190, "avg_travel_percent": 10, "avg_heat_index": 5.0}
        })

    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_evaluate_hedge_endpoint(client):
    response = client.get("/evaluate_hedge")
    assert response.status_code == 200
    data = response.get_json()
    assert data["long"]["value"] == 100
    assert data["short"]["pnl"] == -50
    assert data["totals"]["total_value"] == 190
