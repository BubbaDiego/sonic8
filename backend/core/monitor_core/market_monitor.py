
from datetime import datetime, timezone
from backend.core.monitor_core.base_monitor import BaseMonitor
from backend.data.data_locker import DataLocker
from backend.core.market_core.daily_swing_service import DailySwingService
from backend.core.core_constants import (
    MOTHER_BRAIN_DB_PATH,
    MARKET_MONITOR_BLAST_RADIUS_DEFAULTS,
)




class MarketMonitor(BaseMonitor):
    name = "market_monitor"
    ASSETS = ["BTC", "ETH", "SOL"]

    def __init__(self):
        super().__init__(name=self.name, ledger_filename="market_monitor_ledger.json")
        self.swing = DailySwingService()
        self.dl = DataLocker.get_instance(MOTHER_BRAIN_DB_PATH)

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------
    def _cfg(self):
        cfg = self.dl.system.get_var("market_monitor") or {}
        # default scaffold
        cfg.setdefault("baseline", {})
        cfg.setdefault("thresholds", {})
        cfg.setdefault(
            "blast_filters", {"window": "24h", "exchange": "coingecko"}
        )
        cfg["blast_radius"] = MARKET_MONITOR_BLAST_RADIUS_DEFAULTS.copy()
        # ensure nested defaults
        for asset in self.ASSETS:
            cfg["baseline"].setdefault(
                asset,
                {
                    "price": self.dl.get_latest_price(asset).get("current_price")
                    or 0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "mode": "EITHER",
                },
            )
            cfg["thresholds"].setdefault(asset, 5.0)
        return cfg

    def _save_cfg(self, cfg):
        self.dl.system.set_var("market_monitor", cfg)

    # ------------------------------------------------------------------
    # BaseMonitor override
    # ------------------------------------------------------------------
    def _do_work(self):
        cfg = self._cfg()
        prices = {a: self.dl.get_latest_price(a).get("current_price") for a in self.ASSETS}

        detail = []
        triggered_any = False

        for a in self.ASSETS:
            baseline = cfg["baseline"][a]["price"]
            mode = cfg["baseline"][a]["mode"]
            pct_move = ((prices[a] - baseline) / baseline) * 100 if baseline else 0.0
            threshold = cfg["thresholds"][a]

            hit = (
                (mode == "UP" and pct_move >= threshold) or
                (mode == "DOWN" and pct_move <= -threshold) or
                (mode == "EITHER" and abs(pct_move) >= threshold)
            )
            triggered_any |= hit

            br = MARKET_MONITOR_BLAST_RADIUS_DEFAULTS.get(a, 0.0)

            detail.append({
                "asset": a,
                "price": prices[a],
                "pct_move": round(pct_move, 4),
                "baseline": baseline,
                "blast_radius": round(br, 4),
                "trigger": hit
            })

        return {
            "status": "Success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trigger_any": triggered_any,
            "details": detail
        }

if __name__ == "__main__":
    import json
    from backend.core.logging import log
    monitor = MarketMonitor()
    log.banner("🚀 SELF-RUN: MarketMonitor")
    result = monitor.run_cycle()
    log.success("🧾 MarketMonitor Run Complete", source="SelfTest", payload=result)
    print(json.dumps(result, indent=2))
