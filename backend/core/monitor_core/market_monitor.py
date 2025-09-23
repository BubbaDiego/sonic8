from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from backend.core.monitor_core.base_monitor import BaseMonitor
from backend.data.data_locker import DataLocker


@dataclass
class Anchor:
    value: float = 0.0
    time: str = ""  # ISO8601 timestamp


class MarketMovementMonitor(BaseMonitor):
    """Monitor absolute price movement for configured assets.

    For each asset, an anchor price is recorded. When the latest price moves up or
    down by the configured dollar ``delta`` from that anchor, the monitor triggers
    a notification.

    Rearm behaviour:

    ``ladder`` – move the anchor by ``±delta`` after each trigger so alerts fire
    every ``delta`` dollars.

    ``reset`` – reset the anchor to the current price after a trigger (one alert
    per leg).

    ``single`` – trigger once and disarm until anchors are manually reset.
    """

    name = "market_monitor"
    ASSETS = ["SPX", "BTC", "ETH", "SOL"]

    def __init__(self, dl: DataLocker | None = None):
        super().__init__(name=self.name)
        self.dl = dl or DataLocker.get_instance()

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------
    def _cfg(self) -> Dict[str, Any]:
        cfg = self.dl.system.get_var(self.name) or {}

        cfg.setdefault(
            "notifications",
            {"system": True, "voice": True, "sms": False, "tts": True},
        )
        cfg.setdefault("rearm_mode", "ladder")  # ladder | reset | single
        cfg.setdefault("thresholds", {})  # per asset: {delta, direction}
        cfg.setdefault("anchors", {})  # per asset: {value, time}
        cfg.setdefault("armed", {})  # per asset: bool for 'single' mode

        for asset in self.ASSETS:
            t = cfg["thresholds"].get(asset) or {}
            t.setdefault("delta", 5.0)
            t.setdefault("direction", "both")  # up | down | both
            cfg["thresholds"][asset] = t

            a = cfg["anchors"].get(asset) or {}
            a.setdefault("value", 0.0)
            a.setdefault("time", "")
            cfg["anchors"][asset] = a

            cfg["armed"].setdefault(asset, True)

        self.dl.system.set_var(self.name, cfg)
        return cfg

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------
    def _latest_prices(self) -> Dict[str, float]:
        cur = self.dl.db.get_cursor()
        if cur is None:
            return {a: 0.0 for a in self.ASSETS}

        prices: Dict[str, float] = {}
        for asset in self.ASSETS:
            cur.execute(
                "SELECT current_price, previous_price "
                "FROM prices WHERE asset_type = ? "
                "ORDER BY last_update_time DESC LIMIT 1",
                (asset,),
            )
            row = cur.fetchone()
            val = 0.0
            if row:
                # Be robust to bad historical rows (timestamp accidentally stored
                # in current_price)
                cp = row["current_price"]
                pp = row["previous_price"]
                try:
                    val = float(cp)
                except Exception:
                    try:
                        val = float(pp) if pp is not None else 0.0
                    except Exception:
                        val = 0.0
            prices[asset] = val
        return prices

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------
    def _do_work(self):
        cfg = self._cfg()
        prices = self._latest_prices()
        now = datetime.now(timezone.utc).isoformat()

        triggered_any = False
        details = []
        changed = False

        rearm_mode = str(cfg.get("rearm_mode", "ladder")).lower()

        for asset in self.ASSETS:
            cur_price = float(prices.get(asset, 0.0))
            anc = Anchor(**cfg["anchors"].get(asset, {}))

            # Seed anchor on first run
            if not anc.value:
                cfg["anchors"][asset] = {"value": cur_price, "time": now}
                cfg["armed"][asset] = True
                changed = True
                details.append(
                    {
                        "asset": asset,
                        "status": "anchored",
                        "anchor": cur_price,
                        "current": cur_price,
                    }
                )
                continue

            # Single mode disarms after first alert
            if rearm_mode == "single" and not cfg["armed"].get(asset, True):
                details.append(
                    {
                        "asset": asset,
                        "status": "disarmed",
                        "anchor": anc.value,
                        "current": cur_price,
                    }
                )
                continue

            thr = cfg["thresholds"][asset]
            delta = abs(float(thr.get("delta", 0.0)))
            direction = str(thr.get("direction", "both")).lower()

            if delta <= 0:
                details.append(
                    {
                        "asset": asset,
                        "status": "disabled",
                        "anchor": anc.value,
                        "current": cur_price,
                    }
                )
                continue

            diff = cur_price - anc.value
            move_up = diff >= delta
            move_down = (-diff) >= delta

            hit = (
                (direction == "up" and move_up)
                or (direction == "down" and move_down)
                or (direction == "both" and (move_up or move_down))
            )

            info = {
                "asset": asset,
                "anchor": round(anc.value, 6),
                "current": round(cur_price, 6),
                "delta": delta,
                "direction": direction,
                "move": round(diff, 6),
                "trigger": bool(hit),
            }
            details.append(info)

            if not hit:
                continue

            triggered_any = True
            side = "up" if diff > 0 else "down"
            subject = f"📈 {asset} moved {side} ${abs(diff):.2f} (≥ ${delta:.2f})"
            body = (
                f"{asset}: {anc.value:.2f} → {cur_price:.2f} | anchor @ {anc.value:.2f},"
                f" mode={rearm_mode}/{direction}"
            )
            self._notify("HIGH", subject, body, metadata=info)

            if rearm_mode == "ladder":
                step = delta if side == "up" else -delta
                cfg["anchors"][asset] = {"value": anc.value + step, "time": now}
                changed = True
            elif rearm_mode == "reset":
                cfg["anchors"][asset] = {"value": cur_price, "time": now}
                changed = True
            elif rearm_mode == "single":
                cfg["armed"][asset] = False
                changed = True

        if changed:
            self.dl.system.set_var(self.name, cfg)

        return {
            "triggered": triggered_any,
            "details": details,
            "anchors": cfg.get("anchors", {}),
            "prices": prices,
        }


# Backwards compatibility export
MarketMonitor = MarketMovementMonitor

__all__ = ["MarketMovementMonitor", "MarketMonitor"]

