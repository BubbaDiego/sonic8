#!/usr/bin/env python3
r"""
Seed Sonic DB (system_vars) from backend/config/sonic_monitor_config.json

Usage (Windows):
  cd C:\\sonic7
  .\.venv\Scripts\python.exe backend\scripts\seed_monitor_config_from_json.py
  # optional overrides:
  .\.venv\Scripts\python.exe backend\scripts\seed_monitor_config_from_json.py --json C:\\sonic7\\backend\\config\\sonic_monitor_config.json --db C:\\sonic7\\backend\\mother.db
"""

from __future__ import annotations
import argparse, json, os, sys, re
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# --- repo-local imports (your actual modules) ---
from backend.data.data_locker import DataLocker
from backend.data.dl_system_data import DLSystemDataManager

# ---------- helpers ----------
def _expand_env(node: Any) -> Any:
    """Recursively expand ${VAR} using environment; leave untouched if missing."""
    if isinstance(node, str):
        m = re.fullmatch(r"\$\{([^}]+)\}", node.strip())
        if m:
            return os.getenv(m.group(1), node)
        return node
    if isinstance(node, list):
        return [_expand_env(x) for x in node]
    if isinstance(node, dict):
        return {k: _expand_env(v) for k, v in node.items()}
    return node

def _load_json(path: str) -> Dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f) or {}
            return _expand_env(raw) if isinstance(raw, dict) else {}
    except Exception as e:
        print(f"[seed] ERROR reading JSON: {path} :: {e}")
        return {}

def _coerce_bool(v: Any, default: bool) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on")
    if isinstance(v, (int, float)):
        return bool(v)
    return default

def _coerce_float(v: Any) -> float | None:
    try:
        if v is None: return None
        return float(v)
    except Exception:
        return None

def _coerce_int(v: Any) -> int | None:
    try:
        if v is None: return None
        return int(float(v))
    except Exception:
        return None

def _get(d: Dict, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
    return cur if cur is not None else default

# ---------- seeding ----------
def seed(db_path: str, json_path: str) -> int:
    cfg = _load_json(json_path)
    if not cfg:
        print(f"[seed] WARNING: JSON empty or invalid: {json_path}")
    # DataLocker & system manager
    dal = DataLocker.get_instance(db_path)
    sysmgr = DLSystemDataManager(dal.db)

    wrote = []

    # 1) loop seconds
    loop = _coerce_int(_get(cfg, "monitor", "loop_seconds"))
    if loop is not None:
        sysmgr.set_var("sonic_monitor_loop_time", loop)
        wrote.append(("sonic_monitor_loop_time", loop))

    # 2) liquidation thresholds + blast → alert_thresholds
    thr_map = _get(cfg, "liquid", "thresholds", default={}) or {}
    blast_map = _get(cfg, "liquid", "blast", default={}) or {}
    thr_out, blast_out = {}, {}
    for sym, val in thr_map.items():
        v = _coerce_float(val)
        if v is not None:
            thr_out[str(sym).upper()] = v
            # blast: int or default 0
            b = _coerce_int(blast_map.get(sym, 0))
            blast_out[str(sym).upper()] = int(b or 0)
    if thr_out:
        sysmgr.set_var("alert_thresholds", json.dumps({"thresholds": thr_out, "blast": blast_out}, separators=(",", ":")))
        wrote.append(("alert_thresholds", {"thresholds": thr_out, "blast": blast_out}))

    # 3) profit thresholds (compat keys)
    pos_thr = _coerce_int(_get(cfg, "profit", "position_usd"))
    pf_thr  = _coerce_int(_get(cfg, "profit", "portfolio_usd"))
    if pos_thr is not None:
        sysmgr.set_var("profit_pos", pos_thr)
        wrote.append(("profit_pos", pos_thr))
    if pf_thr is not None:
        sysmgr.set_var("profit_pf", pf_thr)
        sysmgr.set_var("profit_badge_value", pf_thr)  # historical alias
        wrote.append(("profit_pf", pf_thr))

    # 4) per-monitor notification channels → xcom_providers
    # shape supports optional "global" defaults but stores explicit per-monitor flags
    channels = _get(cfg, "channels", default=None)
    # also accept legacy: monitor.notifications like the market schema bundle shows
    #  e.g., cfg["market"]["notifications"] = {system,voice,sms,tts}
    if channels is None:
        channels = {}
        global_default = _get(cfg, "xcom", "channels", default=None) or _get(cfg, "monitor", "notifications", default=None)
        if global_default: channels["global"] = global_default
        for m in ("price", "liquid", "profit", "market"):
            m_notif = _get(cfg, m, "notifications", default=None)
            if m_notif: channels[m] = m_notif

    def _norm_ch(d: dict | None) -> dict:
        d = d or {}
        return {
            "system": _coerce_bool(d.get("system"), True),
            "voice" : _coerce_bool(d.get("voice"),  False),
            "sms"   : _coerce_bool(d.get("sms"),    False),
            "tts"   : _coerce_bool(d.get("tts"),    False),
        }

    if isinstance(channels, dict) and channels is not None:
        global_defaults = _norm_ch(channels.get("global")) if channels.get("global") is not None else {}
        xcom_providers: Dict[str, dict] = {}
        for m in ("price", "liquid", "profit", "market"):
            block = _norm_ch(channels.get(m)) if channels.get(m) is not None else {}
            merged = {"system": True, "voice": False, "sms": False, "tts": False}
            merged.update(global_defaults)
            merged.update(block)
            xcom_providers[m] = merged
        sysmgr.set_var("xcom_providers", json.dumps(xcom_providers, separators=(",", ":")))
        wrote.append(("xcom_providers", xcom_providers))

    # 5) market monitor config → single JSON blob (optional fields supported)
    market = _get(cfg, "market", default=None)
    if isinstance(market, dict) and market:
        # carry through only supported bits; keep notifications too
        market_out = {}
        for k in ("rearm_mode", "assets", "delta_usd", "direction", "anchor", "notifications", "anchors", "baseline", "armed"):
            if market.get(k) is not None:
                market_out[k] = market[k]
        sysmgr.set_var("market_monitor", json.dumps(market_out, separators=(",", ":")))
        wrote.append(("market_monitor", "JSON blob"))

    # summary
    print(f"[seed] DB: {db_path}")
    print(f"[seed] JSON: {json_path}")
    if wrote:
        for k, v in wrote:
            preview = v if isinstance(v, (int, float, str)) else "<json>"
            print(f"[seed] set {k} = {preview}")
    else:
        print("[seed] nothing to write (JSON had no writable keys)")
    return 0

def main():
    backend_dir = Path(__file__).resolve().parents[1]  # .../backend
    default_json = str(backend_dir / "config" / "sonic_monitor_config.json")
    default_db   = os.getenv("SONIC_DB_PATH") or str(backend_dir / "mother.db")

    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=default_json, help="path to sonic_monitor_config.json")
    ap.add_argument("--db",   default=default_db,   help="path to mother.db")
    args = ap.parse_args()

    sys.exit(seed(args.db, args.json))

if __name__ == "__main__":
    main()
