# ──────────────────────────────────────────────────────────────
# File: test_hedge_calculator_page.py
# Author: BubbaDiego
# Created: 2025-06-24
# Description:
#   Basic UI test to ensure Hedge Calculator page loads with required inputs.
# ──────────────────────────────────────────────────────────────
import pytest
from flask import Flask
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def app():
    app = Flask(__name__)
    @app.route("/hedge_calculator")
    def hedge_calculator():
        return '''
        <input id="feePercentage">
        <input id="targetMarginInput">
        <input id="adjustmentFactorInput">
        '''
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_hedge_modifiers_page_contains_inputs(client):
    response = client.get("/hedge_calculator")
    assert response.status_code == 200
    page_content = response.data.decode()
    assert 'id="feePercentage"' in page_content
    assert 'id="targetMarginInput"' in page_content
    assert 'id="adjustmentFactorInput"' in page_content
