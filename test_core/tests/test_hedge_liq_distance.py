# ──────────────────────────────────────────────────────────────
# File: test_hedge_liq_distance.py
# Author: BubbaDiego
# Created: 2025‑06‑24
# Description:
#   Unit tests for liquidation distance suggestions in HedgeCalcServices.
# ──────────────────────────────────────────────────────────────
# tests/test_hedge_liq_distance.py
import pytest
import sys, os

# Correct path insertion
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hedge_calc_services import HedgeCalcServices

@pytest.fixture
def calc():
    return HedgeCalcServices()

@pytest.fixture
def positions():
    return {
        "long": {"entry_price": 100, "size": 500, "collateral": 200, "liquidation_price": 80, "position_type": "LONG"},
        "short": {"entry_price": 100, "size": 500, "collateral": 200, "liquidation_price": 120, "position_type": "SHORT"}
    }

def test_suggest_liq_distance_long(calc, positions):
    result = calc.suggest_liq_distance(
        positions["long"], positions["short"],
        price=100, target_ld_pct=20, adjustable_side="long"
    )
    assert "collateral" in result["updates"]
    assert result["updates"]["collateral"] > positions["long"]["collateral"]

def test_liq_distance_already_safe(calc, positions):
    result = calc.suggest_liq_distance(
        positions["long"], positions["short"],
        price=100, target_ld_pct=5, adjustable_side="long"
    )
    assert "note" in result
    assert result["note"] == "already safe"
