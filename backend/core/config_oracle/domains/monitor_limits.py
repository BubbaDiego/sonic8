# backend/core/config_oracle/domains/monitor_limits.py
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from ..models import (
    MonitorConfigBundle,
    MonitorDefinition,
    MonitorGlobalConfig,
    MonitorNotifications,
)


# --- Coercion helpers --------------------------------------------------------


def _coerce_bool(val: Any, default: bool) -> bool:
    """Loosely coerce user-ish input into a bool."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        v = val.strip().lower()
        if v in ("1", "true", "yes", "on", "y", "t"):
            return True
        if v in ("0", "false", "no", "off", "n", "f"):
            return False
    if isinstance(val, (int, float)):
        return bool(val)
    return default


def _coerce_int(val: Any, default: Optional[int] = None) -> Optional[int]:
    if val is None:
        return default
    try:
        return int(float(val))
    except Exception:
        return default


def _coerce_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    if val is None:
        return default
    try:
        return float(val)
    except Exception:
        return default


def _parse_notifications(
    raw: Optional[Mapping[str, Any]],
    defaults: Optional[MonitorNotifications] = None,
) -> MonitorNotifications:
    """Convert a raw dict of notification booleans into MonitorNotifications."""
    base = defaults or MonitorNotifications()
    raw = raw or {}
    if not isinstance(raw, Mapping):
        raw = {}

    return MonitorNotifications(
        system=_coerce_bool(raw.get("system", base.system), base.system),
        voice=_coerce_bool(raw.get("voice", base.voice), base.voice),
        sms=_coerce_bool(raw.get("sms", base.sms), base.sms),
        tts=_coerce_bool(raw.get("tts", base.tts), base.tts),
    )


# --- Public entrypoint -------------------------------------------------------


def build_monitor_bundle_from_raw(raw: Dict[str, Any]) -> MonitorConfigBundle:
    """
    Build a normalized MonitorConfigBundle from raw JSON.

    Supports two layouts:

    1) Legacy (current) layout, similar to:

        {
          "monitor": {
            "loop_seconds": 30,
            "global_snooze_seconds": 111,
            "enabled": {
              "sonic": true,
              "liquid": true,
              "profit": true,
              "market": true,
              "price": true
            },
            "xcom_live": false
          },
          "liquid": { ... },
          "profit": { ... },
          "market": { ... },
          "price":  { ... },
          "liquid_monitor": { ... },
          "profit_monitor": { ... }
        }

    2) New normalized layout (target structure), e.g.:

        {
          "global": {
            "loop_seconds": 30,
            "global_snooze_seconds": 111,
            "xcom_live": false
          },
          "monitors": {
            "liquid": {
              "enabled": true,
              "notifications": { ... },
              "snooze_seconds": 1200,
              "params": {
                "thresholds": { "BTC": 1.3, "ETH": 1.0 },
                "blast":      { "BTC": 5,   "ETH": 5.0 }
              }
            },
            "profit": {
              "enabled": true,
              "notifications": { ... },
              "params": {
                "position_profit_usd": 10,
                "portfolio_profit_usd": 40
              }
            }
          }
        }

    The Oracle will treat the normalized shape as canonical if present, but
    still supports the legacy structure for a gentle migration path.
    """
    raw = dict(raw or {})
    if "monitors" in raw or "global" in raw:
        return _from_new_style(raw)
    return _from_legacy_style(raw)


# --- New-style config --------------------------------------------------------


def _from_new_style(raw: Dict[str, Any]) -> MonitorConfigBundle:
    global_block = raw.get("global") or {}
    legacy_monitor_block = raw.get("monitor") or {}

    loop = _coerce_int(
        global_block.get("loop_seconds", legacy_monitor_block.get("loop_seconds", 30)),
        default=30,
    )
    if loop is None or loop <= 0:
        loop = 30

    global_snooze = _coerce_int(
        global_block.get(
            "global_snooze_seconds",
            legacy_monitor_block.get("global_snooze_seconds"),
        ),
        default=None,
    )

    xcom_live = _coerce_bool(
        global_block.get("xcom_live", legacy_monitor_block.get("xcom_live", False)),
        default=False,
    )

    global_cfg = MonitorGlobalConfig(
        loop_seconds=loop,
        global_snooze_seconds=global_snooze,
        xcom_live=xcom_live,
    )

    legacy_enabled_map: Dict[str, Any] = {}
    le = legacy_monitor_block.get("enabled")
    if isinstance(le, dict):
        legacy_enabled_map = dict(le)

    monitors: Dict[str, MonitorDefinition] = {}
    monitors_block = raw.get("monitors") or {}
    if isinstance(monitors_block, dict):
        for name, block in monitors_block.items():
            if not isinstance(block, dict):
                continue

            enabled = _coerce_bool(
                block.get("enabled", legacy_enabled_map.get(name, True)),
                default=True,
            )
            snooze = _coerce_int(block.get("snooze_seconds"), default=None)

            notif_raw = block.get("notifications")
            notifications = _parse_notifications(
                notif_raw if isinstance(notif_raw, Mapping) else None
            )

            params = block.get("params") or {}
            if not isinstance(params, dict):
                params = {}

            monitors[name] = MonitorDefinition(
                name=name,
                enabled=enabled,
                notifications=notifications,
                snooze_seconds=snooze,
                params=params,
            )

    # Backfill monitors that only exist in legacy "monitor.enabled"
    for name, val in (legacy_enabled_map or {}).items():
        if name in monitors:
            continue
        monitors[name] = MonitorDefinition(
            name=name,
            enabled=_coerce_bool(val, default=True),
            notifications=MonitorNotifications(),
            snooze_seconds=None,
            params={},
        )

    return MonitorConfigBundle(
        global_config=global_cfg,
        monitors=monitors,
        raw=raw,
    )


# --- Legacy config -----------------------------------------------------------


_LEGACY_KNOWN_MONITORS = ("sonic", "liquid", "profit", "market", "price")


def _from_legacy_style(raw: Dict[str, Any]) -> MonitorConfigBundle:
    monitor_block = raw.get("monitor") or {}

    loop = _coerce_int(monitor_block.get("loop_seconds"), default=30)
    if loop is None or loop <= 0:
        loop = 30

    global_snooze = _coerce_int(
        monitor_block.get("global_snooze_seconds"),
        default=None,
    )
    xcom_live = _coerce_bool(
        monitor_block.get("xcom_live", False),
        default=False,
    )

    global_cfg = MonitorGlobalConfig(
        loop_seconds=loop,
        global_snooze_seconds=global_snooze,
        xcom_live=xcom_live,
    )

    enabled_map: Dict[str, Any] = {}
    em = monitor_block.get("enabled")
    if isinstance(em, dict):
        enabled_map = dict(em)

    candidate_names = set(_LEGACY_KNOWN_MONITORS) | set(enabled_map.keys())
    # If raw has blocks like {"liquid": {...}}, treat those as monitors too.
    for key, val in raw.items():
        if isinstance(val, dict) and key in _LEGACY_KNOWN_MONITORS:
            candidate_names.add(key)

    monitors: Dict[str, MonitorDefinition] = {}

    for name in sorted(candidate_names):
        base_block = raw.get(name)
        if not isinstance(base_block, dict):
            base_block = {}

        mirror_block = raw.get(f"{name}_monitor")
        if not isinstance(mirror_block, dict):
            mirror_block = {}

        notif_raw = base_block.get("notifications")
        notifications = _parse_notifications(
            notif_raw if isinstance(notif_raw, Mapping) else None
        )

        snooze: Optional[int] = None
        if name == "profit":
            snooze = _coerce_int(base_block.get("snooze_seconds"), default=None)
            if snooze is None:
                snooze = _coerce_int(mirror_block.get("snooze_seconds"), default=None)

        params: Dict[str, Any] = {}

        if name == "liquid":
            thresholds = base_block.get("thresholds")
            if not isinstance(thresholds, dict) or not thresholds:
                thresholds = mirror_block.get("thresholds")
                if not isinstance(thresholds, dict):
                    thresholds = {}

            blast = base_block.get("blast")
            if not isinstance(blast, dict) or not blast:
                blast = mirror_block.get("blast")
                if not isinstance(blast, dict):
                    blast = {}

            params["thresholds"] = thresholds
            params["blast"] = blast

        elif name == "profit":
            pos = (
                base_block.get("position_profit_usd")
                or base_block.get("position_usd")
                or mirror_block.get("position_profit_usd")
                or mirror_block.get("position_usd")
            )
            pf = (
                base_block.get("portfolio_profit_usd")
                or base_block.get("portfolio_usd")
                or mirror_block.get("portfolio_profit_usd")
                or mirror_block.get("portfolio_usd")
            )

            pos_f = _coerce_float(pos, default=None)
            pf_f = _coerce_float(pf, default=None)
            if pos_f is not None:
                params["position_profit_usd"] = pos_f
            if pf_f is not None:
                params["portfolio_profit_usd"] = pf_f

        else:
            # For other monitors, carry through any interesting extra knobs in
            # the block(s), excluding keys we already normalize explicitly.
            for block in (base_block, mirror_block):
                if not isinstance(block, dict):
                    continue
                for k, v in block.items():
                    if k in ("notifications", "snooze_seconds"):
                        continue
                    params.setdefault(k, v)

        enabled = _coerce_bool(enabled_map.get(name, True), default=True)

        monitors[name] = MonitorDefinition(
            name=name,
            enabled=enabled,
            notifications=notifications,
            snooze_seconds=snooze,
            params=params,
        )

    return MonitorConfigBundle(
        global_config=global_cfg,
        monitors=monitors,
        raw=raw,
    )
