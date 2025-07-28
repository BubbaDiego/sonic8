import pytest, time
from backend.core.monitor_core.market_monitor import MarketMonitor

def test_window_trigger(tmpdir, dl):
    mm = MarketMonitor(dl=dl)
    asset = "BTC"
    now = int(time.time())

    # seed two price points 24h apart
    dl.db.execute("INSERT INTO prices(asset_type,current_price,last_update_time) VALUES(?,?,?)",
                  (asset, 100, now - 86400))
    dl.db.execute("INSERT INTO prices(asset_type,current_price,last_update_time) VALUES(?,?,?)",
                  (asset, 110, now))

    cfg = mm._cfg()
    cfg['thresholds'][asset]['24h'] = 5.0
    dl.system.set_var(mm.name, cfg)

    payload = mm._do_work()
    btc = [d for d in payload['details'] if d['asset']==asset][0]
    assert btc['windows']['24h']['trigger'] is True