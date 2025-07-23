"""LiquidationMonitor – alerts when positions approach their liquidation price.
Generated July 22, 2025.
"""

from datetime import datetime, timezone, timedelta
from backend.core.monitor_core.base_monitor import BaseMonitor  # type: ignore
from backend.data.data_locker import DataLocker  # type: ignore
from backend.data.dl_positions import DLPositionManager  # type: ignore
from backend.core.xcom_core.xcom_core import XComCore  # type: ignore
from backend.core.logging import log  # type: ignore
from backend.utils.env_utils import _resolve_env
from collections.abc import Mapping
import json

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
        "snooze_seconds": 300,
        "thresholds": {},
    }

    def __init__(self):
        super().__init__(name="liquid_monitor", ledger_filename="liquid_monitor_ledger.json")
        self.dl = DataLocker.get_instance()
        # Pass only the database manager to DLPositionManager
        # instead of the full DataLocker instance
        self.pos_mgr = DLPositionManager(self.dl.db)
        self.xcom = XComCore(self.dl)
        self._last_alert_ts = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_config(self):
        """Load config from system vars with environment overrides."""
        try:
            cfg = self.dl.system.get_var("liquid_monitor") or {}
        except Exception as e:  # pragma: no cover - DB access
            log.error(f"Failed loading liquid monitor config: {e}", source=self.name)
            cfg = {}

        merged = {**self.DEFAULT_CONFIG, **cfg}

        env_map = {
            "threshold_percent": "LIQ_MON_THRESHOLD_PERCENT",
            "level": "LIQ_MON_LEVEL",
            "windows_alert": "LIQ_MON_WINDOWS_ALERT",
            "voice_alert": "LIQ_MON_VOICE_ALERT",
            "snooze_seconds": "LIQ_MON_SNOOZE_SECONDS",
        }

        for key, env_key in env_map.items():
            merged[key] = _resolve_env(merged.get(key), env_key)

        def to_bool(value):
            if isinstance(value, str):
                return value.lower() in ("1", "true", "yes", "on")
            return bool(value)

        try:
            merged["threshold_percent"] = float(merged.get("threshold_percent", 0))
        except Exception:
            merged["threshold_percent"] = float(self.DEFAULT_CONFIG["threshold_percent"])

        try:
            merged["snooze_seconds"] = int(float(merged.get("snooze_seconds", 0)))
        except Exception:
            merged["snooze_seconds"] = int(self.DEFAULT_CONFIG["snooze_seconds"])

        merged["windows_alert"] = to_bool(merged.get("windows_alert"))
        merged["voice_alert"] = to_bool(merged.get("voice_alert"))

        thresholds = merged.get("thresholds", {})
        if isinstance(thresholds, str):
            try:
                thresholds = json.loads(thresholds)
            except Exception:
                thresholds = {}
        if not isinstance(thresholds, Mapping):
            thresholds = {}
        merged["thresholds"] = dict(thresholds)

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

        details = []
        in_danger = []
        for p in positions:
            if p.liquidation_distance is None or p.liquidation_distance == "":
                continue
            try:
                dist = float(p.liquidation_distance)
            except Exception:
                continue
            threshold = cfg.get("thresholds", {}).get(
                getattr(p, "asset_type", None), cfg["threshold_percent"]
            )
            breach = dist <= threshold
            if breach:
                in_danger.append(p)
            log.info(
                f"Asset: {p.asset_type}  Current Liquid Distance: {dist:.2f}  "
                f"Threshold: {threshold:.2f}  Result: {'BREACH' if breach else 'NO BREACH'}",
                source="LiquidationMonitor",
            )
            details.append({
                "asset": p.asset_type,
                "distance": dist,
                "threshold": threshold,
                "breach": breach,
            })

        summary = {
            "total_checked": len(positions),
            "danger_count": len(in_danger),
            "threshold_percent": cfg["threshold_percent"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
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

                SoundService().play("static/sounds/alert_liq.mp3")
            except Exception as e:
                log.warning(f"SoundService unavailable: {e}", source="LiquidationMonitor")

        # XCom escalation
        if cfg["voice_alert"]:
            self.xcom.send_notification(cfg["level"], subject, body, initiator="liquid_monitor")

        self._last_alert_ts = datetime.now(timezone.utc)
        return {**summary, "status": "Success", "alert_sent": True}