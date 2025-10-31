# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

def discover_json_path(default_path: str) -> str:
    p = os.getenv("SONIC_MONITOR_JSON", "").strip()
    if p: return p
    return default_path

def parse_json(path: str) -> tuple[Optional[dict], Optional[str], dict]:
    """Return (obj | None, err | None, meta) meta: {exists,size,mtime}"""
    jp = Path(path); meta = {"exists": jp.exists(), "size": 0, "mtime": "-"}
    if meta["exists"]:
        try:
            meta["size"] = jp.stat().st_size
            meta["mtime"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(jp.stat().st_mtime))
        except Exception:
            pass
    if not meta["exists"]:
        return None, "missing", meta
    try:
        with jp.open("r", encoding="utf-8") as f:
            return json.load(f), None, meta
    except Exception as e:
        return None, f"{type(e).__name__}: {e}", meta

def _num(v, d=None):
    try:
        if v is None: return d
        if isinstance(v, (int,float)): return float(v)
        s = str(v).replace("%"," ").strip()
        return float(s)
    except Exception:
        return d

def _coalesce_profit_keys(p: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """Return normalized (position_usd, portfolio_usd) from varied legacy keys."""

    if not isinstance(p, dict):
        return None, None

    def _pick(keys) -> Optional[float]:
        for key in keys:
            if key in p:
                val = p.get(key)
                if val is not None and val != "":
                    return _num(val)
        return None

    pos_keys = [
        "position_profit_usd",
        "position_usd",
        "single",
        "single_usd",
        "pos",
    ]
    pf_keys = [
        "portfolio_profit_usd",
        "portfolio_usd",
        "portfolio",
        "portfolio_total_usd",
        "total_usd",
        "pf",
    ]

    return _pick(pos_keys), _pick(pf_keys)

def normalize_legacy(obj: dict) -> dict:
    """Accept legacy keys and convert to modern {liquid_monitor, profit_monitor} shape."""
    o = obj or {}
    modern: Dict[str, Any] = {}
    lm = o.get("liquid_monitor") or o.get("liquid") or o.get("liquidation_monitor") or {}
    thr = lm.get("thresholds") or lm.get("thr") or {}
    glob= lm.get("threshold_percent") or lm.get("percent")
    modern["liquid_monitor"] = {"thresholds": {}, **({"threshold_percent": _num(glob)} if glob is not None else {})}
    for s in ("BTC","ETH","SOL"):
        val = thr.get(s)
        if val is not None:
            modern["liquid_monitor"]["thresholds"][s] = _num(val)
    pm = o.get("profit_monitor") or o.get("profit") or {}
    pos, pf = _coalesce_profit_keys(pm)
    modern["profit_monitor"] = {}
    if pos is not None: modern["profit_monitor"]["position_profit_usd"] = pos
    if pf  is not None: modern["profit_monitor"]["portfolio_profit_usd"] = pf
    return modern

def schema_summary(file_obj: Optional[dict], dl) -> dict:
    """
    Return normalized view and sources:
      { liquid: {BTC,ETH,SOL, source}, profit:{pos,pf, source}, json_keys:[...] }
    """
    # FILE
    f = normalize_legacy(file_obj or {})
    file_liq = f.get("liquid_monitor", {})
    file_thr = (file_liq.get("thresholds") or {})
    # DB
    try:
        pm_db = dl.system.get_var("profit_monitor") if getattr(dl, "system", None) else {}
    except Exception:
        pm_db = {}
    pos_db = _num((pm_db or {}).get("position_profit_usd"))
    pf_db  = _num((pm_db or {}).get("portfolio_profit_usd"))

    # choose per-asset (FILE > DB > ENV)
    def choose_liq(sym: str):
        v = _num(file_thr.get(sym))
        src = "FILE" if v is not None else "DB"
        return v, src

    liq = {s: choose_liq(s)[0] for s in ("BTC","ETH","SOL")}
    liq_srcs = {s: choose_liq(s)[1] for s in ("BTC","ETH","SOL")}
    profit = {"pos": pos_db, "pf": pf_db}
    profit_src = "DB" if (pos_db is not None or pf_db is not None) else "—"

    return {
        "json_keys": sorted(list((file_obj or {}).keys())),
        "liquid":   {"BTC": liq["BTC"], "ETH": liq["ETH"], "SOL": liq["SOL"], "source": liq_srcs},
        "profit":   {"pos": profit["pos"], "pf": profit["pf"], "source": profit_src},
        "normalized": f
    }


def _num_env(var: str):
    try:
        v = os.getenv(var)
        return _num(v)
    except Exception:
        return None


def resolve_effective(file_obj: Optional[dict], dl) -> dict:
    """
    JSON → DB → ENV precedence for both Liquid and Profit.
    Returns:
      {
        'liquid': {'BTC':val,'ETH':val,'SOL':val},
        'liquid_src': {'BTC':'FILE|DB|ENV|—', ...},
        'profit': {'pos':val,'pf':val},
        'profit_src': {'pos':'FILE|DB|ENV|—','pf':'FILE|DB|ENV|—'}
      }
    """
    modern = normalize_legacy(file_obj or {})
    # file maps
    f_liq = (modern.get("liquid_monitor") or {}).get("thresholds") or {}
    f_pos = _num((modern.get("profit_monitor") or {}).get("position_profit_usd"))
    f_pf  = _num((modern.get("profit_monitor") or {}).get("portfolio_profit_usd"))
    # db maps
    try:
        lm_db = (dl.system.get_var("liquid_monitor") if getattr(dl, "system", None) else {}) or {}
    except Exception:
        lm_db = {}
    d_thr = (lm_db.get("thresholds") or {})
    d_glob = _num(lm_db.get("threshold_percent"))
    try:
        pm_db = (dl.system.get_var("profit_monitor") if getattr(dl, "system", None) else {}) or {}
    except Exception:
        pm_db = {}
    d_pos = _num(pm_db.get("position_profit_usd"))
    d_pf = _num(pm_db.get("portfolio_profit_usd"))
    # env (last)
    e_map = {
        "BTC": _num_env("LIQUID_THRESHOLD_BTC"),
        "ETH": _num_env("LIQUID_THRESHOLD_ETH"),
        "SOL": _num_env("LIQUID_THRESHOLD_SOL"),
    }
    e_glob = _num_env("LIQUID_THRESHOLD")

    liquid: Dict[str, Optional[float]] = {}
    liquid_src: Dict[str, str] = {}
    for s in ("BTC", "ETH", "SOL"):
        v = _num(f_liq.get(s))
        src = "FILE" if v is not None else None
        if v is None:
            v = _num(d_thr.get(s), d_glob)
            src = "DB" if v is not None else None
        if v is None:
            v = _num(e_map.get(s), e_glob)
            src = "ENV" if v is not None else None
        if v is None:
            src = "—"
        liquid[s] = v
        liquid_src[s] = src or "—"

    # Profit JSON→DB→ENV
    e_pos = _num_env("PROFIT_POSITION_USD")
    e_pf = _num_env("PROFIT_PORTFOLIO_USD")

    def pick(pri, sec, env):
        if pri is not None:
            return pri, "FILE"
        if sec is not None:
            return sec, "DB"
        if env is not None:
            return env, "ENV"
        return None, "—"

    pos_val, pos_src = pick(f_pos, d_pos, e_pos)
    pf_val, pf_src = pick(f_pf, d_pf, e_pf)

    return {
        "liquid": liquid,
        "liquid_src": liquid_src,
        "profit": {"pos": pos_val, "pf": pf_val},
        "profit_src": {"pos": pos_src, "pf": pf_src},
    }
