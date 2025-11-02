# -*- coding: utf-8 -*-
"""
XCOM Check panel – live decision trace:
  • Config source + path
  • Per-monitor channels(liquid) resolved from JSON
  • Readiness (live + no snooze + no voice cooldown)
  • Live breach computation from positions vs thresholds (value ≤ threshold)
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
from backend.data.dl_positions import DLPositionManager  # read active positions
from backend.core.logging import log


def _tick(b: bool) -> str:
    return "✅" if b else "⏭"


def _get_thresholds(cfg: Dict[str, Any]) -> Dict[str, float]:
    """
    Prefer liquid_monitor.thresholds; fallback to liquid.thresholds.
    Normalize keys to upper() and values to float.
    """
    thr = {}
    srcs: List[Tuple[str, Dict[str, Any]]] = []
    if isinstance(cfg.get("liquid_monitor"), dict):
        srcs.append(("liquid_monitor", cfg["liquid_monitor"]))
    if isinstance(cfg.get("liquid"), dict):
        srcs.append(("liquid", cfg["liquid"]))

    for _, section in srcs:
        t = section.get("thresholds") or {}
        if isinstance(t, dict):
            for k, v in t.items():
                try:
                    thr[str(k).upper()] = float(v)
                except Exception:
                    pass
        if thr:
            break  # first source wins
    return thr


def _compute_breaches(dl, thresholds: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Compute live breach from positions: distance <= threshold.
    Returns list of {'asset': 'SOL', 'value': ..., 'threshold': ...}.
    """
    out: List[Dict[str, Any]] = []
    mgr = DLPositionManager(dl.db)
    try:
        positions = mgr.get_active_positions()
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
    # 1) Load JSON exactly like Sync Data uses (so banner/footer agree)
    try:
        cfg_path = discover_json_path(default_json_path)
        cfg_obj, err, meta = parse_json(cfg_path)
        cfg = cfg_obj if isinstance(cfg_obj, dict) else {}
        cfg_src = "FILE"
    except Exception:
        cfg_path = "—"
        cfg = {}
        cfg_src = "RUNTIME"

    # 2) Live probe: XCOM live + per-monitor channels
    live, live_src = xcom_live_status(dl, cfg)
    cfgsvc = XComConfigService(getattr(dl, "system", None), config=cfg)
    ch = cfgsvc.channels_for("liquid")

    # 3) Readiness + cooldown
    ready_ok, reason = xcom_ready(dl, cfg=cfg)
    rem_s, _ = read_voice_cooldown_remaining(dl)

    # 4) Live breach computation from positions vs thresholds
    thresholds = _get_thresholds(cfg)
    breaches = _compute_breaches(dl, thresholds)

    # 5) Print panel
    print("\n  ---------------------- 🔍  XCOM Check  ----------------------")
    print(f"  cfg: {cfg_src} {cfg_path}")
    print(f"  live: {_tick(live)} [{live_src}]")
    phone = f"📞 {_tick(ch.get('voice', False))}"
    sysch = f"🖥️ {_tick(ch.get('system', False))}"
    ttsch = f"🔊 {_tick(ch.get('tts', False))}"
    smsch = f"💬 {_tick(ch.get('sms', False))}"
    print(f"  channels(liquid): {phone}  {sysch}  {ttsch}  {smsch}")

    rd = f"ready: {'✅ ok' if ready_ok else '⏭ ' + str(reason)}"
    cd = f"cooldown: {'idle' if (rem_s or 0) <= 1 else f'{rem_s}s'}"
    print(f"  {rd}  ·  {cd}  ·  breaches: {len(breaches)}")

    if breaches:
        # show a compact list of what we actually saw
        for b in breaches:
            print(f"   • {b['asset']}  {b['value']:.2f} ≤ {b['threshold']:.2f}")

    print("  note: voice fires on breach + rising-edge + cooldown_ok + ready + channel=true")
