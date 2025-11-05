# -*- coding: utf-8 -*-
"""
xcom_panel — explicit gate-by-gate XCOM status (NO rising-edge)

Prints each cycle:
  cfg: FILE <path> | RUNTIME — | EMPTY —
  live: ✅ [FILE] or ⏭ [—]
  channels(liquid): 📞/🖥️/🔊/💬 from monitor-level JSON (XComConfigService)
  provider cooldown: 'idle' or '<seconds>'
  breaches: N  (then each '• ASSET  value ≤ threshold')
  conditions:
    breach                : ✅/⏭
    channel.voice         : ✅/⏭
    xcom_ready            : ✅/⏭  (ok | reason)
    provider_cooldown_ok  : ✅/⏭
    monitor_snoozed=False : ✅/⏭
  note: voice fires when ALL conditions above are ✅
"""

from __future__ import annotations
from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime, timezone

# JSON loader (present in your repo)
from backend.core.reporting_core.sonic_reporting.config_probe import (
    discover_json_path,
    parse_json,
)

# Monitor-level channel resolver
from backend.core.xcom_core.xcom_config_service import XComConfigService

# Provider gates
from backend.core.reporting_core.sonic_reporting.xcom_extras import (
    xcom_ready,
    read_voice_cooldown_remaining,
    xcom_live_status,
)

# Data source
from backend.data.data_locker import DataLocker
from backend.data.dl_positions import DLPositionManager


_IC = {"ok": "✅", "skip": "⏭", "phone": "📞", "sys": "🖥️", "tts": "🔊", "sms": "💬"}


# ---------------- utils ----------------

def _tick(b: bool) -> str:
    return _IC["ok"] if b else _IC["skip"]


def _cfg_from(dl: DataLocker, default_json_path: Optional[str]) -> Tuple[dict, str]:
    """FILE → RUNTIME → EMPTY."""
    # FILE (explicit path)
    if default_json_path:
        try:
            cfg_obj, err, meta = parse_json(default_json_path)
            if isinstance(cfg_obj, dict) and cfg_obj:
                return cfg_obj, f"FILE {default_json_path}"
        except Exception as e:
            print(f"[XCOM] cfg file error: {e}")

    # RUNTIME
    if isinstance(getattr(dl, "global_config", None), dict) and dl.global_config:
        return dl.global_config, "RUNTIME —"

    # Discover FILE
    try:
        p = discover_json_path(None)
        if p:
            cfg_obj, err, meta = parse_json(p)
            if isinstance(cfg_obj, dict) and cfg_obj:
                return cfg_obj, f"FILE {p}"
    except Exception as e:
        print(f"[XCOM] cfg discover error: {e}")

    return {}, "EMPTY —"


def _thresholds(cfg: dict) -> Dict[str, Optional[float]]:
    """Prefer liquid_monitor.thresholds, fall back to liquid.thresholds."""
    thr = {}
    try:
        thr = (cfg.get("liquid_monitor") or {}).get("thresholds") or {}
        if not thr:
            thr = (cfg.get("liquid") or {}).get("thresholds") or {}
    except Exception:
        thr = {}
    out = {}
    for k in ("BTC", "ETH", "SOL"):
        v = thr.get(k)
        try:
            out[k] = float(v) if v is not None else None  # type: ignore
        except Exception:
            out[k] = None  # type: ignore
    return out  # type: ignore


def _channels(cfg: dict, dl: DataLocker) -> Dict[str, bool]:
    """Monitor-level notifications for 'liquid'."""
    try:
        svc = XComConfigService(getattr(dl, "system", None), config=cfg)
        ch = svc.channels_for("liquid") or {}
        return {
            "voice": bool(ch.get("voice", False)),
            "system": bool(ch.get("system", False)),
            "sms": bool(ch.get("sms", False)),
            "tts": bool(ch.get("tts", False)),
        }
    except Exception as e:
        print(f"[XCOM] channels error: {e}")
        return {"voice": False, "system": False, "sms": False, "tts": False}


def _active_breaches(dl: DataLocker, th: Dict[str, Optional[float]]) -> List[dict]:
    """
    Compute live breaches from active positions. rule: dist <= threshold.
    """
    out: List[dict] = []
    try:
        mgr = DLPositionManager(dl.db)
        rows = mgr.get_active_positions() or []
    except Exception as e:
        print(f"[XCOM] positions error: {e}")
        rows = []

    # Take MIN distance per asset
    mins: Dict[str, float] = {}
    for p in rows:
        try:
            sym = str(getattr(p, "asset_type", "") or "").upper()
            if not sym:
                continue
            dist = None
            for k in ("liquidation_distance", "liquidation", "liq", "liq_dist", "liq_pct"):
                v = getattr(p, k, None)
                if v is None:
                    continue
                try:
                    dist = float(v)
                    break
                except Exception:
                    pass
            if dist is None:
                continue
            prev = mins.get(sym)
            if prev is None or dist < prev:
                mins[sym] = dist
        except Exception:
            continue

    for sym, v in mins.items():
        t = th.get(sym)
        if t is None:
            continue
        if v <= t:
            out.append({"asset": sym, "value": v, "threshold": float(t)})
    return out


def _snooze_ok(dl: DataLocker) -> bool:
    """
    Snooze via dl.system['liquid_monitor'] fields:
      snooze_seconds (int), _last_alert_ts (epoch seconds).
    Returns True if NOT snoozed (ok to call).
    """
    try:
        rec = getattr(dl, "system", None)
        rec = rec.get_var("liquid_monitor") if rec else {}
        snooze = (rec or {}).get("snooze_seconds") or 0
        last_ts = (rec or {}).get("_last_alert_ts") or 0
        if not snooze:
            return True
        now = datetime.now(timezone.utc).timestamp()
        return (now - float(last_ts)) >= float(snooze)
    except Exception:
        return True


# ---------------- panel ----------------

def render(dl: Optional[DataLocker], csum: Optional[dict], default_json_path: Optional[str] = None) -> None:
    """
    Lean panel — obtains DL if needed, loads JSON, computes gates, prints results.
    """
    # Ensure DL
    if dl is None:
        try:
            dl = DataLocker.get_instance(r"C:\sonic7\backend\mother.db")
        except Exception:
            dl = DataLocker.get_instance()

    # Config + channels
    cfg, cfg_src = _cfg_from(dl, default_json_path)
    ch = _channels(cfg, dl)

    # Provider readiness + cooldown + live
    try:
        ready_ok, ready_reason = xcom_ready(dl, cfg=cfg)
    except Exception as e:
        ready_ok, ready_reason = False, f"ready-error({e})"

    try:
        rem_s, cd_src = read_voice_cooldown_remaining(dl)
        cooldown_ok = (rem_s <= 0)
    except Exception:
        rem_s, cooldown_ok = 0, True

    try:
        live_on, live_src = xcom_live_status(dl, cfg=getattr(dl, "global_config", None))
    except Exception:
        live_on, live_src = False, "—"

    # Thresholds + breaches (value ≤ threshold)
    thr = _thresholds(cfg)
    breaches = _active_breaches(dl, thr)

    # Snooze (monitor-level)
    snooze_ok = _snooze_ok(dl)

    # Print
    print("\n  ---------------------- 🔍  XCOM Check  ----------------------")
    print(f"  cfg: {cfg_src}")
    print(f"  live: {_IC['ok'] if live_on else _IC['skip']} [{live_src}]")
    print(
        "  channels(liquid):  "
        f"{_IC['phone']} {_tick(ch.get('voice', False))}   "
        f"{_IC['sys']} {_tick(ch.get('system', False))}   "
        f"{_IC['tts']} {_tick(ch.get('tts', False))}   "
        f"{_IC['sms']} {_tick(ch.get('sms', False))}"
    )
    print(f"  provider cooldown: {'idle' if cooldown_ok else f'{int(rem_s)}s'}")
    print(f"  breaches: {len(breaches)}")
    for b in breaches:
        print(f"   • {b['asset']}  {b['value']:.2f} ≤ {b['threshold']:.2f}")

    print("  conditions:")
    print(f"    breach                : {_tick(bool(breaches))}")
    print(f"    channel.voice         : {_tick(ch.get('voice', False))}")
    print(f"    xcom_ready            : {_tick(ready_ok)}  ({'ok' if ready_ok else str(ready_reason)})")
    print(f"    provider_cooldown_ok  : {_tick(cooldown_ok)}")
    print(f"    monitor_snoozed=False : {_tick(snooze_ok)}")
    print("  note: voice fires when ALL conditions above are ✅")
