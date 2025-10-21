import json
import pytest
from backend.data.data_locker import DataLocker


def test_seed_uses_thresholds(tmp_path, monkeypatch):
    config_dir = tmp_path
    (config_dir / "sonic_config.json").write_text(
        json.dumps({
            "liquid_monitor": {"thresholds": {"BTC": 4.0}},
            "price_config": {"assets": ["BTC", "ETH"]}
        })
    )
    monkeypatch.setattr("backend.data.data_locker.CONFIG_DIR", config_dir)
    dl = DataLocker(str(tmp_path / "test.db"))
    cfg = dl.system.get_var("liquid_monitor")
    assert "thresholds" in cfg
    assert cfg["thresholds"]["BTC"] == 4.0
    assert "asset_thresholds" not in cfg


def test_migrates_asset_thresholds(tmp_path, monkeypatch):
    orig = DataLocker._seed_liquid_monitor_config_if_empty
    monkeypatch.setattr(DataLocker, "_seed_liquid_monitor_config_if_empty", lambda self: None)
    dl = DataLocker(str(tmp_path / "test.db"))
    dl.system.set_var("liquid_monitor", {"threshold_percent": 5.0, "asset_thresholds": {"BTC": 3.0}})
    orig(dl)
    cfg = dl.system.get_var("liquid_monitor")
    thresholds = cfg.get("thresholds") or {}
    assert thresholds.get("BTC") == 3.0
    from backend.core.monitor_core.liquidation_monitor import LiquidationMonitor

    for asset, default in LiquidationMonitor.DEFAULT_ASSET_THRESHOLDS.items():
        if asset != "BTC":
            assert thresholds.get(asset) == default
    assert "threshold_percent" not in cfg
    assert "asset_thresholds" not in cfg


