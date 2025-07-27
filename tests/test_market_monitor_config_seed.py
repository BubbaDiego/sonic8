import pytest
from backend.data.data_locker import DataLocker


def test_market_monitor_seed_defaults(tmp_path):
    dl = DataLocker(str(tmp_path / "test.db"))
    cfg = dl.system.get_var("market_monitor")
    assert set(cfg.get("baseline", {})) == {"BTC", "ETH", "SOL"}
    assert all(v["mode"] == "EITHER" for v in cfg["baseline"].values())
    assert cfg["thresholds"] == {"BTC": 5.0, "ETH": 5.0, "SOL": 5.0}
    assert cfg["blast_radius"] == {"BTC": 8000.0, "ETH": 300.0, "SOL": 13.0}
    assert cfg["blast_filters"] == {"window": "24h", "exchange": "coingecko"}
