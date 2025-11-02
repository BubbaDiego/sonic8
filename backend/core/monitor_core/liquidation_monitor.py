# -*- coding: utf-8 -*-
"""
LiquidationMonitor — alerts when positions approach their liquidation price.

This version aligns the dispatch path with the consolidated XCOM stack:
- Uses XComConfigService.channels_for('liquid') to decide if voice is enabled.
- Calls backend.core.xcom_core.dispatch_notifications (unified path).
- Adds high-signal debug at every gate in the decision chain.
- Blast radius remains display-only (no gating).

Compatible with BaseMonitor + existing console output.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from collections.abc import Mapping
import json
import os
import time
from typing import Optional

from backend.core.monitor_core.base_monitor import BaseMonitor  # type: ignore
from backend.data.data_locker import DataLocker  # type: ignore
from backend.data.dl_positions import DLPositionManager  # type: ignore
from backend.core.logging import log  # type: ignore
from backend.utils.env_utils import _resolve_env  # type: ignore

# consolidated XCOM stack
from backend.core.xcom_core import dispatch_notifications
from backend.core.xcom_core.xcom_config_service import XComConfigService
from backend.core.reporting_core.sonic_reporting.xcom_extras import xcom_ready

# --- Rising-edge + cooldown helpers (per asset) ------------------------------
_LIQ_LAST_HIT: dict[str, bool] = {}
_LIQ_LAST_NOTIFY_AT: dict[str, float] = {}
_LIQ_NOTIFY_COOLDOWN_S = int(os.getenv("LIQUID_NOTIFY_COOLDOWN_S", "180"))


def _rising_edge(asset: str, hit: bool) -> bool:
    prev = _LIQ_LAST_HIT.get(asset, False)
    _LIQ_LAST_HIT[asset] = hit
    return hit and not prev


def _cooldown_ok(asset: str, now: float) -> bool:
    last = _LIQ_LAST_NOTIFY_AT.get(asset, 0.0)
    return (now - last) >= _LIQ_NOTIFY_COOLDOWN_S


def _mark_notified(asset: str, when: Optional[float] = None) -> None:
    _LIQ_LAST_NOTIFY_AT[asset] = float(when or time.time())


def _maybe_clear_queue_on_safe(ctx, asset: str) -> None:
    """Best-effort: if asset flips back to safe, clear any queued voice item."""
    svc = (
        getattr(ctx.dl, "voice_service", None)
        or getattr(ctx.dl, "xcom_voice", None)
        or getattr(ctx.dl, "xcom", None)
        or getattr(ctx.dl, "voice", None)
    )
    try:
        if svc and hasattr(svc, "clear"):
            try:
                svc.clear("liquid", asset)
            except TypeError:
                svc.clear({"monitor": "liquid", "asset": asset})
    except Exception:
        pass


class LiquidationMonitor(BaseMonitor):
    """
    Config key: ``liquid_monitor``

    JSON slice (example):

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
        "windows_alert": True,   # legacy toggles still honored for system/sms
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
        self._last_alert_ts: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_config(self):
        """Load config from system vars with environment overrides."""
        try:
            cfg = self.dl.system.get_var("liquid_monitor") or {}
        except Exception as e:  # pragma: no cover
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

        def to_bool(v):
            if isinstance(v, str):
                return v.lower() in ("1", "true", "yes", "on")
            return bool(v)

        try:
            merged["snooze_seconds"] = int(float(merged.get("snooze_seconds", 0)))
        except Exception:
            merged["snooze_seconds"] = int(self.DEFAULT_CONFIG["snooze_seconds"])

        # Parse thresholds
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

        # Parse notifications (system/sms/tts). Voice is resolved via XComConfigService.
        notifications = merged.get("notifications", {})
        if isinstance(notifications, str):
            try:
                notifications = json.loads(notifications)
            except Exception:
                notifications = {}
        if not isinstance(notifications, Mapping):
            notifications = {}
        notifications = {
            "system": to_bool(notifications.get("system", merged["windows_alert"])),
            "voice": to_bool(notifications.get("voice", merged["voice_alert"])),
            "sms": to_bool(notifications.get("sms", merged["sms_alert"])),
            "tts": to_bool(notifications.get("tts", True)),
        }
        merged["notifications"] = notifications

        merged["enabled"] = to_bool(merged.get("enabled", True))
        merged["windows_alert"] = notifications["system"]
        merged["voice_alert"]   = notifications["voice"]
        merged["sms_alert"]     = notifications["sms"]

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
        if not cfg.get("enabled", True):
            log.info("LiquidationMonitor disabled; skipping cycle", source=self.name)
            return {"status": "Disabled", "success": True}

        # Effective channels for THIS monitor (from JSON/DB)
        cfg_service = XComConfigService(self.dl.system, config=getattr(self.dl, "global_config", None))
        channels_for_monitor = cfg_service.channels_for("liquid")
        voice_enabled = bool(channels_for_monitor.get("voice", False))
        log.debug(
            "XCOM channels_for(liquid) => %s",
            channels_for_monitor,
            source="LiquidationMonitor",
        )

        positions = self.pos_mgr.get_active_positions()
        thresholds = cfg.get("thresholds", {})
        notif = cfg.get("notifications") or {}

        details = []
        in_danger = []
        alert_lines: list[str] = []

        for p in positions:
            if p.liquidation_distance is None or p.liquidation_distance == "":
                continue
            try:
                dist = float(p.liquidation_distance)
            except Exception:
                continue

            threshold = self._resolve_threshold(getattr(p, "asset_type", None), thresholds)
            asset_key = str(getattr(p, "asset_type", "") or "UNKNOWN").upper()
            now_ts = time.time()

            breach = dist <= threshold
            if breach:
                in_danger.append(p)
                try:
                    line = (
                        f"{p.asset_type} {p.position_type} at {p.current_price:.2f} – "
                        f"liq {p.liquidation_price:.2f} ({p.liquidation_distance:.2f}% away)"
                    )
                except Exception:
                    line = f"{asset_key} {getattr(p, 'position_type', '—')} ≤ {threshold:.2f}% (distance {dist:.2f}%)"
                alert_lines.append(line)

                r_edge = _rising_edge(asset_key, True)
                cd_ok  = _cooldown_ok(asset_key, now_ts)
                snoozed = self._snoozed(cfg)
                ready_ok, ready_reason = xcom_ready(self.dl, cfg=getattr(self.dl, "global_config", None))

                log.debug(
                    "liq: asset=%s breach=%s dist=%.2f thr=%.2f rising_edge=%s cooldown_ok=%s snoozed=%s voice_enabled=%s xcom_ready=%s(%s)",
                    asset_key, breach, dist, threshold, r_edge, cd_ok, snoozed, voice_enabled, ready_ok, ready_reason or "ok",
                    source="LiquidationMonitor",
                )

                will_dispatch = breach and r_edge and cd_ok and voice_enabled and ready_ok and not snoozed
                if will_dispatch:
                    _mark_notified(asset_key, now_ts)
                    # One consolidated call; channels=None → use JSON/DB defaults (channels.liquid.voice)
                    summary = dispatch_notifications(
                        monitor_name="liquid",
                        result={"breach": True, "summary": line},
                        channels=None,
                        context={
                            "subject": f"⚠️ {asset_key} near liquidation",
                            "body": line,
                            "asset": asset_key,
                        },
                        db_path=self.dl.db_path,
                    )
                    log.info(
                        "XCOM voice dispatch result",
                        source="LiquidationMonitor",
                        payload={"voice": summary.get("channels", {}).get("voice", {}), "success": summary.get("success")},
                    )
                else:
                    # Flip back to safe if needed (and clear queue)
                    pass
            else:
                if _LIQ_LAST_HIT.get(asset_key, False):
                    _LIQ_LAST_HIT[asset_key] = False
                    _maybe_clear_queue_on_safe(self, asset_key)

            log.info(
                f"Asset: {getattr(p, 'asset_type', '—')}  Current Liquid Distance: {dist:.2f}  "
                f"Threshold: {threshold:.2f}  Result: {'BREACH' if breach else 'NO BREACH'}",
                source="LiquidationMonitor",
            )
            details.append(
                {"asset": getattr(p, "asset_type", None), "distance": dist, "threshold": threshold, "breach": breach}
            )

        summary = {
            "total_checked": len(positions),
            "danger_count": len(in_danger),
            "thresholds": dict(thresholds),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
        }

        # End-of-loop “batch” side channels (system / tts / sms).
        if not in_danger or self._snoozed(cfg):
            return {**summary, "status": "Success", "alert_sent": False}

        # Build body text
        subject = f"⚠️ {len(alert_lines)} position(s) near liquidation"
        body = "\n".join(alert_lines)

        # Local system sound
        if notif.get("system"):
            log.info("System sound alert dispatched", source="LiquidationMonitor")
            try:
                from backend.core.xcom_core.sound_service import SoundService  # type: ignore
                SoundService().play("frontend/static/sounds/alert_liq.mp3")
            except Exception as e:
                log.warning(f"SoundService unavailable: {e}", source="LiquidationMonitor")

        # TTS (through XCom voice provider when enabled; otherwise no-op)
        if notif.get("tts", True):
            dispatch_notifications(
                monitor_name="liquid",
                result={"breach": True, "summary": "Liquidation is a concern"},
                channels=["tts"],  # explicit to avoid voice here
                context={"subject": subject, "body": "Liquidation is a concern"},
                db_path=self.dl.db_path,
            )

        # SMS stub (if/when provider gets wired)
        if notif.get("sms"):
            dispatch_notifications(
                monitor_name="liquid",
                result={"breach": True, "summary": body},
                channels=["sms"],  # explicit to avoid voice here
                context={"subject": subject, "body": body},
                db_path=self.dl.db_path,
            )

        self._last_alert_ts = datetime.now(timezone.utc)
        try:
            cfg_record = self.dl.system.get_var("liquid_monitor") or {}
            cfg_record["_last_alert_ts"] = self._last_alert_ts.timestamp()
            self.dl.system.set_var("liquid_monitor", cfg_record)
        except Exception as e:  # best effort
            log.warning(f"Failed to persist last alert timestamp: {e}", source="LiquidationMonitor")

        return {**summary, "status": "Success", "alert_sent": True}
