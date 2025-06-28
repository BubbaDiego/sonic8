
import pytest
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from hedge_core.hedge_calc_services import HedgeCalcServices

@pytest.fixture
def calc():
    return HedgeCalcServices()

@pytest.fixture
def positions():
    return {
        "long": {"entry_price": 100, "size": 1000, "collateral": 500, "position_type": "LONG"},
        "short": {"entry_price": 100, "size": 1000, "collateral": 500, "position_type": "SHORT"}
    }

def test_evaluate_at_price_basic(calc, positions):
    eval_data = calc.evaluate_at_price(positions["long"], positions["short"], 105)
    assert eval_data["long"]["pnl"] == 50.0
    assert eval_data["short"]["pnl"] == -50.0
    assert eval_data["net"]["pnl"] == 0.0

def test_suggest_rebalance_equal_value_collateral(calc, positions):
    config = {"adjustment_target": "equal_value", "adjustable_side": "long"}
    suggestion = calc.suggest_rebalance(positions["long"], positions["short"], 105, config)
    assert "collateral" in suggestion["updates"]
    assert suggestion["side"] == "long"
