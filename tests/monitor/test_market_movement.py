import time
from backend.data.data_locker import DataLocker
from backend.core.monitor_core.market_monitor import MarketMonitor


def test_window_trigger(tmp_path):
    dl = DataLocker(str(tmp_path / "test.db"))
    mm = MarketMonitor(dl=dl)
    now = int(time.time())
    cur = dl.db.get_cursor()
    cur.execute(
        "INSERT INTO prices(asset_type,current_price,last_update_time) VALUES(?,?,?)",
        ("BTC", 100, now - 86400)
    )
    cur.execute(
        "INSERT INTO prices(asset_type,current_price,last_update_time) VALUES(?,?,?)",
        ("BTC", 110, now)
    )
    dl.db.commit()
    cfg = mm._cfg()
    cfg["thresholds"]["BTC"]["24h"] = 5.0
    dl.system.set_var(mm.name, cfg)
    payload = mm._do_work()
    btc = next(d for d in payload["details"] if d["asset"] == "BTC")
    assert btc["windows"]["24h"]["trigger"] is True
