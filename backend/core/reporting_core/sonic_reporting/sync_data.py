# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, Optional, List, Tuple
import os

from .writer import write_table
from .state import set_resolved
from .config_probe import (
    discover_json_path,
    parse_json,
    schema_summary,
    resolve_effective,
)

# Icons
ICON_BTC = "🟡"
ICON_ETH = "🔷"
ICON_SOL = "🟣"
ICON_MON = "🖥️"   # section marker requested earlier
ICON_PROF_ROW = "💵"
ICON_LIQ_ROW  = "💧"

def _ok(b: bool) -> str:
    return "✅" if b else "❌"

def _chk(b: bool) -> str:
    return "✓" if b else "✗"

def _fmt_num(v: Optional[float]) -> str:
    try:
        if v is None:
            return "—"
        s = f"{float(v):.2f}".rstrip("0").rstrip(".")
        return s
    except Exception:
        return "—"

def _indent_block(s: str, spaces: int = 2) -> str:
    pad = " " * spaces
    s = "\n".join(line.rstrip() for line in s.splitlines())
    s = s.replace("\n\n", "\n").strip()
    return "\n".join(pad + line for line in s.splitlines())

# ------------ XCOM Live probe (runtime → file → db → env) ------------
def _as_bool(val) -> Tuple[bool, bool]:
    if isinstance(val, bool):
        return True, val
    if isinstance(val, (int, float)):
        return True, bool(val)
    if isinstance(val, str):
        v = val.strip().lower()
        if v in ("1","true","on","yes","y"):  return True, True
        if v in ("0","false","off","no","n"): return True, False
    return False, False

def _probe_obj_bool(obj, names: List[str]) -> Optional[bool]:
    for n in names:
        try:
            attr = getattr(obj, n, None)
        except Exception:
            attr = None
        # attribute
        ok, b = _as_bool(attr)
        if ok:
            return b
        # method
        if callable(attr):
            try:
                rv = attr()
                ok2, b2 = _as_bool(rv)
                if ok2:
                    return b2
            except Exception:
                pass
    return None

def _xcom_live_status(dl) -> Tuple[bool, str]:
    """
    True/False and the source used: RUNTIME | FILE | DB | ENV | —
    """
    # 1) RUNTIME (DataLocker services)
    try:
        for name in ("voice_service", "xcom_voice", "xcom", "voice"):
            svc = getattr(dl, name, None)
            if not svc:
                continue
            # object/properties/methods
            val = _probe_obj_bool(svc, ["is_live","live","enabled","is_enabled","active","is_active"])
            if val is not None:
                return bool(val), "RUNTIME"
            # dict-like values
            if isinstance(svc, dict):
                for key in ("is_live","live","enabled","is_enabled","active","is_active"):
                    if key in svc:
                        ok, b = _as_bool(svc.get(key))
                        if ok: return b, "RUNTIME"
    except Exception:
        pass

    # 2) FILE (global_config)
    try:
        gc = getattr(dl, "global_config", None) or {}
        channels = gc.get("channels") or {}
        voice = channels.get("voice") or gc.get("xcom") or {}
        for key in ("enabled","active","live","is_live","is_enabled"):
            if key in voice:
                ok, b = _as_bool(voice.get(key))
                if ok: return b, "FILE"
    except Exception:
        pass

    # 3) DB (system vars)
    try:
        sysvars = getattr(dl, "system", None)
        if sysvars:
            var = (sysvars.get_var("xcom") or {})
            for key in ("live","is_live","enabled","is_enabled","active"):
                if key in var:
                    ok, b = _as_bool(var.get(key))
                    if ok: return b, "DB"
    except Exception:
        pass

    # 4) ENV
    env = os.getenv("XCOM_LIVE", os.getenv("XCOM_ACTIVE", ""))
    ok, b = _as_bool(env)
    if ok:
        return b, "ENV"

    return False, "—"

# ------------------------------ RENDER ------------------------------
def render(dl, csum: Dict[str, Any], default_json_path: str) -> None:
    """
    Sync Data table:
      - XCOM Live row (🟢 ON / 🔴 OFF) with origin in brackets.
      - Config/Parse rows
      - Compact Schema check
      - JSON→DB→ENV line
      - Multi-line Liquid/Profit thresholds with per-item origin
    """

    json_path = discover_json_path(default_json_path)
    obj, err, meta = parse_json(json_path)
    exists = bool(meta.get("exists"))
    size = meta.get("size", "—")

    summ = schema_summary(obj if isinstance(obj, dict) else None, dl)
    resolved = resolve_effective(obj if isinstance(obj, dict) else None, dl)
    set_resolved(csum, resolved)

    rows: List[List[str]] = []

    # XCOM Live — runtime-first, with colored word via emoji
    live, src = _xcom_live_status(dl)
    rows.append([
        "🛰 XCOM Live",
        "🟢 ON" if live else "🔴 OFF",
        f"[{src}]"
    ])

    # Config JSON path
    rows.append([
        "📦 Config JSON path",
        _ok(exists),
        f"{json_path}  [exists {_chk(exists)}, {size} bytes]"
    ])

    # Parse JSON
    if err:
        rows.append(["🧪 Parse JSON", _ok(False), f"error: {err}"])
    else:
        keys = ", ".join((obj or {}).keys()) if isinstance(obj, dict) else "—"
        rows.append(["🧪 Parse JSON", _ok(True), f"keys=({keys})"])

    # Schema check — compact with icons
    lm = summ["normalized"].get("liquid_monitor", {}) or {}
    tm = (lm.get("thresholds") or {}) if isinstance(lm, dict) else {}
    btc_ok = "BTC" in tm
    eth_ok = "ETH" in tm
    sol_ok = "SOL" in tm
    pm = summ["normalized"].get("profit_monitor", {}) or {}
    pos_ok = "position_profit_usd" in pm
    pf_ok  = "portfolio_profit_usd" in pm

    schema_all_ok = bool(lm) and bool(tm) and btc_ok and eth_ok and sol_ok and bool(pm) and pos_ok and pf_ok
    schema_details = (
        f"{ICON_MON}mon {_chk(bool(lm))} · thr {_chk(bool(tm))} · "
        f"{ICON_BTC}BTC {_chk(btc_ok)} · {ICON_ETH}ETH {_chk(eth_ok)} · {ICON_SOL}SOL {_chk(sol_ok)} · "
        f"{ICON_MON}mon {_chk(bool(pm))} · pos {_chk(pos_ok)} · pf {_chk(pf_ok)}"
    )
    rows.append(["🔎 Schema check", _ok(schema_all_ok), schema_details])

    # Resolved summary
    rows.append(["🧭 Read monitor thresholds", _ok(True), "JSON→DB→ENV"])

    # Liquid thresholds (compact multi-line with per-asset origin)
    lmap = resolved.get("liquid", {}) or {}
    lsrc = resolved.get("liquid_src", {}) or {}
    btc_r = _fmt_num(lmap.get("BTC"))
    eth_r = _fmt_num(lmap.get("ETH"))
    sol_r = _fmt_num(lmap.get("SOL"))

    liquid_status = _ok(all(x != "—" for x in (btc_r, eth_r, sol_r)))
    liquid_block = (
        f"{ICON_BTC} BTC {btc_r} ({lsrc.get('BTC','—')})\n"
        f"{ICON_ETH} ETH {eth_r} ({lsrc.get('ETH','—')})\n"
        f"{ICON_SOL} SOL {sol_r} ({lsrc.get('SOL','—')})"
    )
    rows.append([f"{ICON_LIQ_ROW} Liquid thresholds", liquid_status, _indent_block(liquid_block, 2)])

    # Profit thresholds (compact multi-line with per-field origin)
    pmap = resolved.get("profit", {}) or {}
    psrc = resolved.get("profit_src", {}) or {}
    pos_r = pmap.get("pos")
    pf_r  = pmap.get("pf")

    profit_status = _ok(pos_r is not None and pf_r is not None)
    pos_str = f"${int(pos_r)}" if isinstance(pos_r, (int, float)) else ("—" if pos_r is None else f"${pos_r}")
    pf_str  = f"${int(pf_r)}"  if isinstance(pf_r,  (int, float)) else ("—" if pf_r  is None else f"${pf_r}")

    profit_block = (
        f"👤 Single {pos_str} ({psrc.get('pos','—')})\n"
        f"🧺 Portfolio {pf_str} ({psrc.get('pf','—')})"
    )
    rows.append([f"{ICON_PROF_ROW} Profit thresholds", profit_status, _indent_block(profit_block, 2)])

    # Render table (sequencer prints the dashed section header)
    write_table(title=None, headers=["Activity", "Status", "Details"], rows=rows)
