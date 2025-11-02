# -*- coding: utf-8 -*-
"""
XCOM Check – explicit gate-by-gate status (no rising-edge here).
"""

from __future__ import annotations
from typing import Any, Dict, Optional, List, Tuple

from backend.core.reporting_core.sonic_reporting.config_probe import (
    discover_json_path,
    parse_json,
)
from backend.core.xcom_core.xcom_config_service import XComConfigService
from backend.core.reporting_core.sonic_reporting.xcom_extras import (
    xcom_ready,
    read_voice_cooldown_remaining,
    xcom_live_status,
)
from backend.data.dl_positions import DLPositionManager
from backend.core.logging import log


def _tick(b: bool) -> str:
    return "✅" if b else "⏭"


def _get_thresholds(cfg: Dict[str, Any]) -> Dict[str, float]:
    """Prefer liquid_monitor.thresholds; fallback to liquid.thresholds. Uppercase keys."""
    thr = {}
    for sec_key in ("liquid_monitor", "liquid"):
        sec = cfg.get(sec_key)
        if isinstance(sec, dict):
            t = sec.get("thresholds") or {}
            if isinstance(t, dict):
                for k, v in t.items():
                    try:
                        thr[str(k).upper()] = float(v)
                    except Exception:
                        pass
            if thr:
                break
    return thr


def _compute_breaches(dl, thresholds: Dict[str, float]) -> List[Dict[str, Any]]:
    """Compute live breach from positions: distance <= threshold."""
    out: List[Dict[str, Any]] = []
    try:
        positions = DLPositionManager(dl.db).get_active_positions()
    except Exception as e:
        log.debug("XCOM Check: cannot fetch positions", source="xcom_check", payload={"error": str(e)})
        return out

    for p in positions:
        try:
            dist = float(p.liquidation_distance)
        except Exception:
            continue
        asset = str(getattr(p, "asset_type", "") or "UNKNOWN").upper()
        thr = float(thresholds.get(asset, 0.0))
        if thr and dist <= thr:
            out.append({"asset": asset, "value": dist, "threshold": thr})
    return out


def render(dl, csum: Dict[str, Any], default_json_path: Optional[str] = None) -> None:
    # 1) JSON same as Sync Data
    try:
        cfg_path = discover_json_path(default_json_path)
        cfg_obj, _, _ = parse_json(cfg_path)
        cfg = cfg_obj if isinstance(cfg_obj, dict) else {}
        cfg_src = "FILE"
    except Exception:
        cfg_path = "—"
        cfg = {}
        cfg_src = "RUNTIME"

    # 2) Live status + monitor channels
    live, live_src = xcom_live_status(dl, cfg)
    cfgsvc = XComConfigService(getattr(dl, "system", None), config=cfg)
    ch = cfgsvc.channels_for("liquid")

    # 3) Readiness + provider cooldown
    ready_ok, reason = xcom_ready(dl, cfg=cfg)
    cd_rem, _ = read_voice_cooldown_remaining(dl)
    provider_cooldown_ok = (cd_rem or 0) <= 1

    # 4) Live breaches
    thresholds = _get_thresholds(cfg)
    breaches = _compute_breaches(dl, thresholds)

    # 5) Monitor snooze (global window)
    snooze_ok = True
    try:
        lm = dl.system.get_var("liquid_monitor") or {}
        last = lm.get("_last_alert_ts")
        szz = int(lm.get("snooze_seconds", cfg.get("liquid_monitor", {}).get("snooze_seconds", 0)) or 0)
        if last and szz > 0:
            import time as _t
            snooze_ok = (_t.time() - float(last)) >= szz
    except Exception:
        pass

    # 6) Print panel
    print("\n  ---------------------- 🔍  XCOM Check  ----------------------")
    print(f"  cfg: {cfg_src} {cfg_path}")
    print(f"  live: {_tick(live)} [{live_src}]")
    print(f"  channels(liquid):  📞 {_tick(ch.get('voice', False))}   🖥️ {_tick(ch.get('system', False))}   🔊 {_tick(ch.get('tts', False))}   💬 {_tick(ch.get('sms', False))}")
    print(f"  provider cooldown: {'idle' if provider_cooldown_ok else f'{cd_rem}s'}")
    print(f"  breaches: {len(breaches)}")
    for b in breaches:
        print(f"   • {b['asset']}  {b['value']:.2f} ≤ {b['threshold']:.2f}")

    # 7) Explicit gate results (the only gates that matter — no rising-edge here)
    print("  conditions:")
    print(f"    breach                : {_tick(bool(breaches))}")
    print(f"    channel.voice         : {_tick(ch.get('voice', False))}")
    print(f"    xcom_ready            : {_tick(ready_ok)}  ({'ok' if ready_ok else str(reason)})")
    print(f"    provider_cooldown_ok  : {_tick(provider_cooldown_ok)}")
    print(f"    monitor_snoozed=False : {_tick(snooze_ok)}")

    print("  note: voice fires when ALL conditions above are ✅")
