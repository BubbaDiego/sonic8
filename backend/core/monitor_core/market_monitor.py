from datetime import datetime, timezone
from backend.core.monitor_core.base_monitor import BaseMonitor
from backend.data.data_locker import DataLocker
from backend.core.core_constants import MARKET_MONITOR_BLAST_RADIUS_DEFAULTS as _BLAST_DEFAULTS

# Re-export constant for backwards compatibility
MARKET_MONITOR_BLAST_RADIUS_DEFAULTS = _BLAST_DEFAULTS


class MarketMonitor(BaseMonitor):
    name    = "market_monitor"
    ASSETS  = ["SPX", "BTC", "ETH", "SOL"]
    WINDOWS = {                                   # we keep it lean for now
        "1h" : 60 * 60,
        "6h" : 6  * 60 * 60,
        "24h": 24 * 60 * 60,
    }

    def __init__(self, dl: DataLocker | None = None):
        super().__init__(name=self.name)
        self.dl = dl or DataLocker.get_instance()

    def _cfg(self):
        cfg = self.dl.system.get_var(self.name) or {}
        cfg.setdefault("thresholds", {})
        cfg.setdefault("baseline", {})

        for asset in self.ASSETS:
            cfg["baseline"].setdefault(asset, {"value": 0, "time": 0})
            cur = cfg["thresholds"].get(asset, 5.0)
            if isinstance(cur, (int, float, str)):
                cur = {"24h": float(cur)}
            cfg["thresholds"][asset] = {**{w: 2.0 for w in self.WINDOWS}, **cur}

        self.dl.system.set_var(self.name, cfg)
        return cfg

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _price_at(self, asset: str, seconds_ago: int) -> float:
        ts_cut = datetime.now(timezone.utc).timestamp() - seconds_ago
        cur = self.dl.db.get_cursor()
        if cur is None:
            return 0.0
        cur.execute(
            "SELECT current_price FROM prices "
            "WHERE asset_type = ? "
            "AND strftime('%s', last_update_time) <= ? "
            "ORDER BY last_update_time DESC LIMIT 1",
            (asset, ts_cut),
        )
        row = cur.fetchone()
        return float(row["current_price"]) if row else 0.0

    # ------------------------------------------------------------------ #
    # Core
    # ------------------------------------------------------------------ #
    def _latest_prices(self) -> dict:
        return {
            a: (self.dl.get_latest_price(a).get("current_price") or 0.0)
            for a in self.ASSETS
        }

    def _do_work(self):
        cfg = self._cfg()
        prices = self._latest_prices()
        results = []
        flagged = False

        for asset in self.ASSETS:
            cur = prices[asset]
            windows_data = {}
            for win, secs in self.WINDOWS.items():
                prev = self._price_at(asset, secs) or cur
                if prev == 0:
                    pct = 0.0
                else:
                    pct = (cur - prev) / prev * 100.0
                thr = cfg["thresholds"][asset][win]
                hit = abs(pct) >= thr
                windows_data[win] = {
                    "pct_move": round(pct, 4),
                    "threshold": thr,
                    "trigger": hit,
                }
                flagged |= hit

            results.append({"asset": asset, "windows": windows_data})

        return {"triggered": flagged, "details": results}


__all__ = ["MarketMonitor", "MARKET_MONITOR_BLAST_RADIUS_DEFAULTS"]

