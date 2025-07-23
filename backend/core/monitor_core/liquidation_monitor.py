"""LiquidationMonitor – alerts when positions approach their liquidation price.
Generated July 22, 2025.
"""

from datetime import datetime, timezone, timedelta
from backend.core.monitor_core.base_monitor import BaseMonitor  # type: ignore
from backend.data.data_locker import DataLocker  # type: ignore
from backend.data.dl_positions import DLPositionManager  # type: ignore
from backend.core.xcom_core.xcom_core import XComCore  # type: ignore
from backend.core.logging import log  # type: ignore

class LiquidationMonitor(BaseMonitor):
    """Check active positions: if liquidation_distance <= threshold_percent → alert.

    Config key: ``liquid_monitor``

    Example JSON slice::

        {
          "liquid_monitor": {
            "threshold_percent": 5.0,
            "level": "HIGH",
            "windows_alert": true,
            "voice_alert": true,
            "snooze_seconds": 300
          }
        }
    """

    DEFAULT_CONFIG = {
        "threshold_percent": 5.0,
        "level": "HIGH",
        "windows_alert": True,
        "voice_alert": True,
        "snooze_seconds": 300
    }

    def __init__(self):
        super().__init__(name="liquid_monitor", ledger_filename="liquid_monitor_ledger.json")
        self.dl = DataLocker.get_instance()
        self.pos_mgr = DLPositionManager(self.dl)
        self.xcom = XComCore(self.dl)
        self._last_alert_ts = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_config(self):
        cfg = self.dl.config.get_section("liquid_monitor") or {}
        merged = {**self.DEFAULT_CONFIG, **cfg}
        merged["threshold_percent"] = float(merged["threshold_percent"])
        merged["snooze_seconds"] = int(merged["snooze_seconds"])
        return merged

    def _snoozed(self, cfg: dict) -> bool:
        if not self._last_alert_ts:
            return False
        delta = datetime.now(timezone.utc) - self._last_alert_ts
        return delta < timedelta(seconds=cfg["snooze_seconds"])

    # ------------------------------------------------------------------
    # BaseMonitor requirement
    # ------------------------------------------------------------------
    def _do_work(self):
        cfg = self._get_config()
        positions = self.pos_mgr.get_active_positions()

        in_danger = [
            p for p in positions
            if p.liquidation_distance is not None
            and p.liquidation_distance != ""
            and float(p.liquidation_distance) <= cfg["threshold_percent"]
        ]

        summary = {
            "total_checked": len(positions),
            "danger_count": len(in_danger),
            "threshold_percent": cfg["threshold_percent"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if not in_danger or self._snoozed(cfg):
            return {**summary, "status": "Success", "alert_sent": False}

        # Build alert payload
        lines = [
            f"{p.asset_type} {p.position_type} at {p.current_price:.2f} – liq {p.liquidation_price:.2f} ({p.liquidation_distance:.2f}% away)"
            for p in in_danger
        ]
        subject = f"⚠️ {len(in_danger)} position(s) near liquidation"
        body = "\n".join(lines)

        # Local sound / toast
        if cfg["windows_alert"]:
            try:
                from backend.core.xcom_core.sound_service import SoundService  # type: ignore

                SoundService({"enabled": True}).play("static/sounds/alert_liq.mp3")
            except Exception as e:
                log.warning(f"SoundService unavailable: {e}", source="LiquidationMonitor")

        # XCom escalation
        if cfg["voice_alert"]:
            self.xcom.send_notification(cfg["level"], subject, body, initiator="liquid_monitor")

        self._last_alert_ts = datetime.now(timezone.utc)
        return {**summary, "status": "Success", "alert_sent": True}