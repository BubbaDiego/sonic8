# -*- coding: utf-8 -*-
"""
LiquidationMonitor — alerts when positions approach their liquidation price.

Requested behavior:
- REMOVE rising-edge gating entirely.
- KEEP a simple per-asset local cooldown; if condition is still true after cooldown, retrigger.
- Continue to honor consolidated XCOM readiness + provider cooldown + per-monitor channels.

This version:
- Uses XComConfigService.channels_for('liquid') to decide if voice is enabled.
- Calls backend.core.xcom_core.dispatch_notifications (unified path).
- Logs a clear INFO "XCOM[GATE]" line for each breached asset every cycle.
- Blast radius remains display-only (no gating).
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from collections.abc import Mapping
import pathlib
import json
import os
import time
from typing import Optional

from backend.core.monitor_core.base_monitor import BaseMonitor  # type: ignore
from backend.data.data_locker import DataLocker  # type: ignore
from backend.data.dl_positions import DLPositionManager  # type: ignore
from backend.core.logging import log  # type: ignore
from backend.utils.env_utils import _resolve_env  # type: ignore

from backend.core.xcom_core import dispatch_notifications
from backend.core.xcom_core.xcom_config_service import XComConfigService
from backend.core.reporting_core.sonic_reporting.xcom_extras import xcom_ready
from backend.core.reporting_core.sonic_reporting.config_probe import discover_json_path, parse_json

# ── Local per-asset notify cooldown (provider cooldown still applies) ─────────
_LIQ_LAST_NOTIFY_AT: dict[str, float] = {}
_LIQ_NOTIFY_COOLDOWN_S = int(os.getenv("LIQUID_NOTIFY_COOLDOWN_S", "180"))  # set "0" to disable local cooldown


def _cooldown_ok(asset: str, now: float) -> bool:
    last = _LIQ_LAST_NOTIFY_AT.get(asset, 0.0)
    return (now - last) >= _LIQ_NOTIFY_COOLDOWN_S


def _mark_notified(asset: str, when: Optional[float] = None) -> None:
    _LIQ_LAST_NOTIFY_AT[asset] = float(when or time.time())


class LiquidationMonitor(BaseMonitor):
    """Config key: ``liquid_monitor``"""

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

        # loud announce of module + version
        print(f"[LM] loaded LM/no-edge+pepper+filecfg v1")

        # robust JSON load (announce success/failure explicitly)
        self._file_cfg, self._cfg_path, self._cfg_src = self._load_file_cfg()
        if self._file_cfg:
            print(f"[LM][CFG] ✅ source={self._cfg_src} path={self._cfg_path} keys={len(self._file_cfg)}")
        else:
            print(f"[LM][CFG] ❌ no usable config (source={self._cfg_src} path={self._cfg_path}) — falling back to empty")

    def _read_positions_resilient(self):
        """
        1) Try active positions (normal path).
        2) If none (e.g., importer failed), fall back to last-known rows in DB.
           We pick the most recent per-asset where liquidation_distance is not NULL.
        """
        # 1) Normal path
        try:
            active = self.pos_mgr.get_active_positions()
        except Exception:
            active = []
        if active:
            print(f"[LM] positions: active={len(active)}  fallback=0  using=active")
            return active

        # 2) Fallback (stale/cached)
        fallback = []
        try:
            cur = self.dl.db.get_cursor()
            if cur:
                # NOTE: Adjust table/column names if your schema differs.
                # This query picks most recent per-asset by updated_at (or created_at if needed).
                cur.execute(
                    """
                        SELECT p1.*
                        FROM positions p1
                        JOIN (
                            SELECT asset_type, MAX(COALESCE(updated_at, created_at)) AS ts
                            FROM positions
                            WHERE liquidation_distance IS NOT NULL AND liquidation_distance != ''
                            GROUP BY asset_type
                        ) px
                        ON p1.asset_type = px.asset_type
                       AND COALESCE(p1.updated_at, p1.created_at) = px.ts
                    """
                )
                cols = [d[0] for d in cur.description]
                for row in cur.fetchall():
                    rec = dict(zip(cols, row))

                    class _Row:
                        pass

                    obj = _Row()
                    for k, v in rec.items():
                        setattr(obj, k, v)
                    fallback.append(obj)
        except Exception as e:
            print(f"[LM] fallback query failed: {e}")

        print(
            f"[LM] positions: active=0  fallback={len(fallback)}  using={'fallback' if fallback else 'none'}"
        )
        return fallback

    def _load_file_cfg(self) -> tuple[dict, str, str]:
        """
        Loud, robust config loader:
          1) dl.global_config if present & non-empty (RUNTIME)
          2) discover_json_path (FILE)
          3) canonical backend/config/sonic_monitor_config.json (FILE)
        Returns (cfg_dict, path_str, source_label). Never silent.
        """
        # 1) RUNTIME – dl.global_config
        try:
            gc = getattr(self.dl, "global_config", None)
            if isinstance(gc, dict) and gc:
                return gc, "dl.global_config", "RUNTIME"
        except Exception as e:
            print(f"[LM][CFG] RUNTIME load error: {e}")

        # 2) FILE – discover_json_path
        try:
            default_guess = os.environ.get("SONIC_CONFIG_JSON", None) or None
            cfg_path = discover_json_path(default_guess)
            if cfg_path:
                cfg_obj, err, meta = parse_json(cfg_path)
                if isinstance(cfg_obj, dict) and cfg_obj:
                    return cfg_obj, str(cfg_path), "FILE"
                else:
                    print(f"[LM][CFG] FILE parse returned empty (err={err}) path={cfg_path}")
            else:
                print("[LM][CFG] discover_json_path returned None")
        except Exception as e:
            print(f"[LM][CFG] FILE discover/parse error: {e}")

        # 3) FILE – canonical fallback
        try:
            here = pathlib.Path(__file__).resolve()
            fallback = (here.parent.parent.parent / "config" / "sonic_monitor_config.json").resolve()
            if fallback.is_file():
                cfg_obj, err, meta = parse_json(str(fallback))
                if isinstance(cfg_obj, dict) and cfg_obj:
                    return cfg_obj, str(fallback), "FILE"
                else:
                    print(f"[LM][CFG] canonical parse returned empty (err={err}) path={fallback}")
            else:
                print(f"[LM][CFG] canonical path not found: {fallback}")
        except Exception as e:
            print(f"[LM][CFG] canonical parse error: {e}")

        # Nothing worked
        return {}, "—", "NONE"

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

        # thresholds
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

        # notifications (system/sms/tts only; voice resolved via XComConfigService)
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

        # Use FILE cfg we loaded above for resolver so channels/liquid reflects JSON every cycle
        cfg_service = XComConfigService(self.dl.system, config=self._file_cfg)
        ch = cfg_service.channels_for("liquid")
        voice_enabled = bool(ch.get("voice", False))
        print(
            f"[LM][CHAN] voice={ch.get('voice', False)} system={ch.get('system', False)} "
            f"tts={ch.get('tts', False)} sms={ch.get('sms', False)} (cfg_src={self._cfg_src})"
        )

        positions = self._read_positions_resilient()
        if not positions:
            print("[LM] no positions available this cycle (import errors or empty DB); skipping dial")
            return {"status": "NoPositions", "success": True, "details": []}
        thresholds = cfg.get("thresholds", {}) or {}
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

            asset_key = str(getattr(p, "asset_type", "") or "UNKNOWN").upper()
            threshold = self._resolve_threshold(asset_key, thresholds)
            breach = dist <= threshold
            now_ts = time.time()

            if breach:
                in_danger.append(p)
                try:
                    line = (
                        f"{p.asset_type} {p.position_type} at {p.current_price:.2f} – "
                        f"liq {p.liquidation_price:.2f} ({float(p.liquidation_distance):.2f}% away)"
                    )
                except Exception:
                    line = f"{asset_key} ≤ {threshold:.2f}% (dist {dist:.2f}%)"
                alert_lines.append(line)

                cd_ok  = _cooldown_ok(asset_key, now_ts) if _LIQ_NOTIFY_COOLDOWN_S > 0 else True
                snoozed = self._snoozed(cfg)
                ready_ok, ready_reason = xcom_ready(self.dl, cfg=getattr(self.dl, "global_config", None))

                # INFO trace every cycle for breached assets
                log.info(
                    "XCOM[GATE] asset=%s breach=%s dist=%.2f thr=%.2f local_cooldown_ok=%s snoozed=%s voice_enabled=%s xcom_ready=%s(%s)",
                    asset_key, breach, dist, threshold, cd_ok, snoozed, voice_enabled, ready_ok, ready_reason or "ok",
                    source="LiquidationMonitor",
                )

                will_dispatch = breach and cd_ok and voice_enabled and ready_ok and not snoozed
                if will_dispatch:
                    _mark_notified(asset_key, now_ts)
                    summary = dispatch_notifications(
                        monitor_name="liquid",
                        result={"breach": True, "summary": line},
                        channels=None,  # use per-monitor JSON
                        context={"subject": f"⚠️ {asset_key} near liquidation", "body": line, "asset": asset_key},
                        db_path=self.dl.db_path,
                    )
                    log.info(
                        "XCOM[VOICE] result",
                        source="LiquidationMonitor",
                        payload={"voice": summary.get("channels", {}).get("voice", {}), "success": summary.get("success")},
                    )

            log.info(
                f"Asset: {getattr(p, 'asset_type', asset_key)}  Current Liquid Distance: {dist:.2f}  "
                f"Threshold: {threshold:.2f}  Result: {'BREACH' if breach else 'NO BREACH'}",
                source="LiquidationMonitor",
            )
            details.append(
                {"asset": getattr(p, "asset_type", asset_key), "distance": dist, "threshold": threshold, "breach": breach}
            )

        summary = {
            "total_checked": len(positions),
            "danger_count": len(in_danger),
            "thresholds": dict(thresholds),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
        }

        # End-of-loop side channels
        if not in_danger or self._snoozed(cfg):
            return {**summary, "status": "Success", "alert_sent": False}

        subject = f"⚠️ {len(alert_lines)} position(s) near liquidation"
        body = "\n".join(alert_lines)

        if notif.get("system"):
            log.info("System sound alert dispatched", source="LiquidationMonitor")
            try:
                from backend.core.xcom_core.sound_service import SoundService  # type: ignore
                SoundService().play("frontend/static/sounds/alert_liq.mp3")
            except Exception as e:
                log.warning(f"SoundService unavailable: {e}", source="LiquidationMonitor")

        if notif.get("tts", True):
            dispatch_notifications(
                monitor_name="liquid",
                result={"breach": True, "summary": "Liquidation is a concern"},
                channels=["tts"],
                context={"subject": subject, "body": "Liquidation is a concern"},
                db_path=self.dl.db_path,
            )

        if notif.get("sms"):
            dispatch_notifications(
                monitor_name="liquid",
                result={"breach": True, "summary": body},
                channels=["sms"],
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
