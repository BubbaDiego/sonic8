import pytest
from backend.data.data_locker import DataLocker
from backend.core.core_constants import MARKET_MONITOR_BLAST_RADIUS_DEFAULTS


def test_market_monitor_seed_defaults(tmp_path):
    dl = DataLocker(str(tmp_path / "test.db"))
    cfg = dl.system.get_var("market_monitor")
    assert set(cfg.get("baseline", {})) == {"BTC", "ETH", "SOL"}
    assert all(v["mode"] == "EITHER" for v in cfg["baseline"].values())
    assert cfg["thresholds"] == {"BTC": 5.0, "ETH": 5.0, "SOL": 5.0}
    assert cfg["blast_radius"] == MARKET_MONITOR_BLAST_RADIUS_DEFAULTS
    assert cfg["blast_filters"] == {"window": "24h", "exchange": "coingecko"}
