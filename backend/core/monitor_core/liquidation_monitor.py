"""LiquidationMonitor – alerts when positions approach their liquidation price.

v3 – October 2025
• Global threshold overrides removed (per-asset only).
• Nested ``notifications`` dict (system / voice / sms / tts).
"""

from datetime import datetime, timezone, timedelta
from collections.abc import Mapping
import json
import os

from backend.core.monitor_core.base_monitor import BaseMonitor  # type: ignore
from backend.data.data_locker import DataLocker  # type: ignore
from backend.data.dl_positions import DLPositionManager  # type: ignore
from backend.core.xcom_core.xcom_core import XComCore  # type: ignore
from backend.core.logging import log  # type: ignore
from backend.utils.env_utils import _resolve_env  # type: ignore

class LiquidationMonitor(BaseMonitor):
    """Check active positions: emit alerts when liquidation distance breaches thresholds.

    Config key: ``liquid_monitor``

    Example JSON slice::

        {
          "liquid_monitor": {
            "snooze_seconds": 300,
            "thresholds": { "BTC": 5, "ETH": 8, "SOL": 7 },
            "notifications": { "system": true, "voice": true, "sms": false, "tts": true }
          }
        }
    """

    DEFAULT_THRESHOLD = 5.0
    DEFAULT_ASSET_THRESHOLDS = {"BTC": DEFAULT_THRESHOLD, "ETH": DEFAULT_THRESHOLD, "SOL": DEFAULT_THRESHOLD}
    _WARNED_ENV = False

    DEFAULT_CONFIG = {
        "level": "HIGH",
        "windows_alert": True,   # kept for env overrides / CLI
        "voice_alert": True,
        "sms_alert": False,
        "snooze_seconds": 300,
        "thresholds": {},
        "notifications": {"system": True, "voice": True, "sms": False, "tts": True},
        "enabled": True,
    }

    def __init__(self):
        super().__init__(name="liquid_monitor", ledger_filename="liquid_monitor_ledger.json")
        self.dl = DataLocker.get_instance()
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
            "level": "LIQ_MON_LEVEL",
            "windows_alert": "LIQ_MON_WINDOWS_ALERT",
            "voice_alert": "LIQ_MON_VOICE_ALERT",
            "sms_alert": "LIQ_MON_SMS_ALERT",
            "snooze_seconds": "LIQ_MON_SNOOZE_SECONDS",
            "enabled": "LIQ_MON_ENABLED",
        }

        for key, env_key in env_map.items():
            merged[key] = _resolve_env(merged.get(key), env_key)

        if not self.__class__._WARNED_ENV and os.getenv("LIQ_MON_THRESHOLD_PERCENT") is not None:
            self.__class__._WARNED_ENV = True
            log.warning(
                "LIQ_MON_THRESHOLD_PERCENT is ignored; configure per-asset thresholds instead.",
                source=self.name,
            )

        def to_bool(value):
            if isinstance(value, str):
                return value.lower() in ("1", "true", "yes", "on")
            return bool(value)

        try:
            merged["snooze_seconds"] = int(float(merged.get("snooze_seconds", 0)))
        except Exception:
            merged["snooze_seconds"] = int(self.DEFAULT_CONFIG["snooze_seconds"])

        # Legacy boolean keys
        merged["windows_alert"] = to_bool(merged.get("windows_alert"))
        merged["voice_alert"] = to_bool(merged.get("voice_alert"))
        merged["sms_alert"] = to_bool(merged.get("sms_alert"))

        # Parse thresholds dict (per‑asset)
        thresholds = merged.get("thresholds", {})
        if isinstance(thresholds, str):
            try:
                thresholds = json.loads(thresholds)
            except Exception:
                thresholds = {}
        if not isinstance(thresholds, Mapping):
            thresholds = {}

        normalized: dict[str, float] = {}
        for key, value in dict(thresholds).items():
            asset = str(key).upper()
            try:
                normalized[asset] = float(value)
            except Exception:
                continue

        for asset, default_value in self.DEFAULT_ASSET_THRESHOLDS.items():
            normalized.setdefault(asset, float(default_value))

        merged["thresholds"] = normalized
        merged.pop("threshold_percent", None)

        # Parse notifications dict – ensure booleans and sync with legacy keys
        notifications = merged.get("notifications", {})
        if isinstance(notifications, str):
            try:
                notifications = json.loads(notifications)
            except Exception:
                notifications = {}
        if not isinstance(notifications, Mapping):
            notifications = {}

        # Fill missing keys with legacy values / defaults
        notifications = {
            "system": to_bool(notifications.get("system", merged["windows_alert"])),
            "voice": to_bool(notifications.get("voice", merged["voice_alert"])),
            "sms": to_bool(notifications.get("sms", merged["sms_alert"])),
            "tts": to_bool(notifications.get("tts", True)),
        }
        merged["notifications"] = notifications

        # Ensure enabled is boolean
        merged["enabled"] = to_bool(merged.get("enabled", True))

        # Keep the top‑level flags in sync (so env overrides still work)
        merged["windows_alert"] = notifications["system"]
        merged["voice_alert"] = notifications["voice"]
        merged["sms_alert"] = notifications["sms"]

        return merged

    def _resolve_threshold(self, asset: str | None, thresholds: Mapping[str, float]) -> float:
        if asset:
            key = str(asset).upper()
            if key in thresholds:
                try:
                    return float(thresholds[key])
                except Exception:
                    pass
            if key in self.DEFAULT_ASSET_THRESHOLDS:
                return float(self.DEFAULT_ASSET_THRESHOLDS[key])
        return float(self.DEFAULT_THRESHOLD)

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

        # ╭──────────────────────────────────────────────╮
        # │ Respect the master enable/disable switch     │
        # ╰──────────────────────────────────────────────╯
        if not cfg.get("enabled", True):
            log.info("LiquidationMonitor disabled; skipping cycle", source=self.name)
            return {"status": "Disabled", "success": True}

        positions = self.pos_mgr.get_active_positions()

        log.debug(f"Liquidation cfg: {cfg}", source="LiquidationMonitor")

        details = []
        in_danger = []
        thresholds = cfg.get("thresholds", {})
        for p in positions:
            if p.liquidation_distance is None or p.liquidation_distance == "":
                continue
            try:
                dist = float(p.liquidation_distance)
            except Exception:
                continue
            threshold = self._resolve_threshold(getattr(p, "asset_type", None), thresholds)
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
            "thresholds": dict(thresholds),
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

        # Notification routing
        notif = cfg["notifications"]
        # Local system sound / toast
        if notif.get("system"):
            log.info("System sound alert dispatched", source="LiquidationMonitor")
            try:
                from backend.core.xcom_core.sound_service import SoundService  # type: ignore
                SoundService().play("frontend/static/sounds/alert_liq.mp3")
            except Exception as e:
                log.warning(f"SoundService unavailable: {e}", source="LiquidationMonitor")

        if notif.get("tts", True):
            self.xcom.send_notification(
                cfg["level"], subject, "Liquidation is a concern", initiator="liquid_monitor", mode="tts"
            )

        # Voice call
        if notif.get("voice"):
            log.info("Voice alert dispatched", source="LiquidationMonitor")
            self.xcom.send_notification(
                cfg["level"], subject, body, initiator="liquid_monitor", mode="voice"
            )

        # SMS (stub – mode recognised but might no‑op until provider wired)
        if notif.get("sms"):
            log.info("SMS alert dispatched", source="LiquidationMonitor")
            self.xcom.send_notification(
                cfg["level"], subject, body, initiator="liquid_monitor", mode="sms"
            )

        self._last_alert_ts = datetime.now(timezone.utc)
        # Persist last alert timestamp for cross-process visibility
        try:
            cfg_record = self.dl.system.get_var("liquid_monitor") or {}
            cfg_record["_last_alert_ts"] = self._last_alert_ts.timestamp()
            self.dl.system.set_var("liquid_monitor", cfg_record)
        except Exception as e:  # pragma: no cover - best effort persistence
            log.warning(
                f"Failed to persist last alert timestamp: {e}",
                source="LiquidationMonitor",
            )

        return {**summary, "status": "Success", "alert_sent": True}
