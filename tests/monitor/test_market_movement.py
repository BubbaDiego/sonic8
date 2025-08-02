from datetime import datetime, timedelta, timezone
from backend.data.data_locker import DataLocker
from backend.core.monitor_core.market_monitor import MarketMonitor


def test_window_trigger(tmp_path):
    dl = DataLocker(str(tmp_path / "test.db"))
    mm = MarketMonitor(dl=dl)
    now = datetime.now(timezone.utc)
    dl.prices.insert_price({
        "asset_type": "BTC",
        "current_price": 100,
        "previous_price": 0,
        "previous_update_time": None,
        "last_update_time": (now - timedelta(days=1)).isoformat(),
        "source": "test",
    })
    dl.prices.insert_price({
        "asset_type": "BTC",
        "current_price": 110,
        "previous_price": 100,
        "previous_update_time": (now - timedelta(days=1)).isoformat(),
        "last_update_time": now.isoformat(),
        "source": "test",
    })
    cfg = mm._cfg()
    cfg["thresholds"]["BTC"]["24h"] = 5.0
    dl.system.set_var(mm.name, cfg)
    payload = mm._do_work()
    btc = next(d for d in payload["details"] if d["asset"] == "BTC")
    assert btc["windows"]["24h"]["trigger"] is True
    assert btc["windows"]["24h"]["pct_move"] != 0
