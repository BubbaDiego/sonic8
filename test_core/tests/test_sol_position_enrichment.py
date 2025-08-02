import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.data.data_locker import DataLocker
from backend.core.positions_core.position_enrichment_service import (
    PositionEnrichmentService,
)


def test_sol_position_enrichment_sets_liq_distance(tmp_path, monkeypatch):
    """SOL positions should retain asset_type and compute liquidation distance."""

    # Avoid seeders during the test
    monkeypatch.setattr(DataLocker, "_seed_modifiers_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_wallets_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_thresholds_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_alerts_if_empty", lambda self: None)

    db_path = tmp_path / "positions.db"
    dl = DataLocker(str(db_path))

    pos = {
        "id": "sol1",
        "asset_type": "SOL",
        "entry_price": 100.0,
        "current_price": 120.0,
        "liquidation_price": 50.0,
        "value": 0.0,
        "collateral": 500.0,
        "size": 5.0,
        "leverage": 2.0,
        "position_type": "LONG",
        "wallet_name": "test",
        "current_heat_index": 0.0,
        "pnl_after_fees_usd": 0.0,
        "travel_percent": 0.0,
        "liquidation_distance": 0.0,
        "heat_index": 0.0,
        "last_updated": "2024-01-01T00:00:00",
    }
    svc = PositionEnrichmentService(dl)
    enriched = svc.enrich(pos)

    assert enriched["asset_type"] == "SOL"
    assert isinstance(enriched.get("liquidation_distance"), (int, float))
    assert enriched["liquidation_distance"] == pytest.approx(70.0)

