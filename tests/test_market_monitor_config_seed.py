from backend.data.data_locker import DataLocker


def test_market_monitor_seed_defaults(tmp_path):
    dl = DataLocker(str(tmp_path / "test.db"))
    cfg = dl.system.get_var("market_monitor")

    assert cfg["rearm_mode"] == "ladder"
    for asset in ["SPX", "BTC", "ETH", "SOL"]:
        assert cfg["thresholds"][asset]["delta"] == 5.0
        assert cfg["thresholds"][asset]["direction"] == "both"
        assert cfg["anchors"][asset]["value"] == 0.0
