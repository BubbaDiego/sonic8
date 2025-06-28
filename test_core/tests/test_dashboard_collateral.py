import types

import dashboard.dashboard_service as ds

class DummyDL:
    def __init__(self):
        self.db = types.SimpleNamespace(get_cursor=lambda: None, commit=lambda: None)
        self.ledger = types.SimpleNamespace(get_status=lambda name: {})
        self.portfolio = types.SimpleNamespace(get_snapshots=lambda: [])
        self.hedges = types.SimpleNamespace(get_hedges=lambda: [])
        self.system = types.SimpleNamespace(get_theme_mode=lambda: "dark")
    def read_wallets(self):
        return []

def test_collateral_none_handled(monkeypatch):
    positions = [
        {"id": "1", "position_type": "LONG", "collateral": None, "size": 1.0},
        {"id": "2", "position_type": "SHORT", "collateral": 5.0, "size": 2.0},
    ]

    monkeypatch.setattr(ds, "PositionCore", lambda dl: types.SimpleNamespace(get_active_positions=lambda: positions))
    monkeypatch.setattr(ds, "CalculationCore", lambda dl: types.SimpleNamespace(
        calc_services=ds.CalcServices(),
        aggregate_positions_and_update=lambda pos, db: pos,
    ))
    monkeypatch.setattr(ds, "SystemCore", lambda dl: types.SimpleNamespace(get_portfolio_thresholds=lambda: {}))

    ctx = ds.get_dashboard_context(DummyDL())
    assert ctx["collateral_composition"]["series"] == [0, 100]
