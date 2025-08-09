from datetime import datetime, timedelta, timezone

import pytest

from backend.data.data_locker import DataLocker
from backend.core.monitor_core.market_monitor import MarketMonitor


def test_trigger_and_rearm(tmp_path):
    dl = DataLocker(str(tmp_path / "test.db"))
    mm = MarketMonitor(dl=dl)

    now = datetime.now(timezone.utc)
    dl.prices.insert_price(
        {
            "asset_type": "BTC",
            "current_price": 100.0,
            "previous_price": 0.0,
            "previous_update_time": None,
            "last_update_time": (now - timedelta(minutes=1)).isoformat(),
            "source": "test",
        }
    )

    # First run seeds anchor at 100
    mm._do_work()

    cfg = dl.system.get_var(mm.name)
    cfg["thresholds"]["BTC"]["delta"] = 10.0
    dl.system.set_var(mm.name, cfg)

    dl.prices.insert_price(
        {
            "asset_type": "BTC",
            "current_price": 112.0,
            "previous_price": 100.0,
            "previous_update_time": (now - timedelta(minutes=1)).isoformat(),
            "last_update_time": now.isoformat(),
            "source": "test",
        }
    )

    payload = mm._do_work()
    btc = next(d for d in payload["details"] if d["asset"] == "BTC")
    assert btc["trigger"] is True

    cfg = dl.system.get_var(mm.name)
    # Ladder mode moves anchor by delta (100 + 10)
    assert cfg["anchors"]["BTC"]["value"] == pytest.approx(110.0)
