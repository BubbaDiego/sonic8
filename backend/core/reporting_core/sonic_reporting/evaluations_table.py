# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, Tuple, Optional
from .writer import write_table
from .state import get_resolved

def _num(v, d=None):
    try:
        if v is None: return d
        if isinstance(v, (int,float)): return float(v)
        return float(str(v).replace("%",""))
    except Exception:
        return d

def _fmt_num(v): 
    return "—" if v is None else f"{_num(v):.2f}".rstrip("0").rstrip(".")

def _fmt_usd(v):
    return "—" if v is None else f"${float(v):.2f}".rstrip("0").rstrip(".")

def build_rows(dl, csum: Dict[str, Any]) -> Tuple[list[list[str]], Optional[str]]:
    # Use resolved JSON-first thresholds cached by sync_cycle
    resolved = get_resolved(csum) or {}
    lmap = (resolved.get("liquid") or {})
    lsrcs = (resolved.get("liquid_src") or {})
    pmap = (resolved.get("profit") or {})
    psrcs = (resolved.get("profit_src") or {})
    single_thr = _num(pmap.get("pos"))
    port_thr = _num(pmap.get("pf"))

    # nearest liquidation distance per asset from snapshot table if cycle_id available; fallback to positions
    nearest = {}
    try:
        cur = dl.db.get_cursor()
        if csum.get("cycle_id"):
            cur.execute("SELECT asset, MIN(ABS(liquidation_distance)) FROM sonic_positions WHERE cycle_id=? GROUP BY asset", (csum["cycle_id"],))
        else:
            cur.execute("SELECT asset_type, MIN(ABS(liquidation_distance)) FROM positions WHERE status='ACTIVE' GROUP BY asset_type")
        for a, d in cur.fetchall() or []:
            nearest[str(a).upper()] = _num(d)
    except Exception:
        pass

    title_ts = None
    try:
        t = (csum.get("positions") or {}).get("ts") or (csum.get("prices") or {}).get("ts")
        title_ts = t
    except Exception:
        pass

    rows = []
    def add_liq(sym, icon):
        actual = nearest.get(sym)
        thr = _num(lmap.get(sym))
        rule = "≤"
        result = "· no data" if actual is None else ("🔴 HIT" if (thr is not None and actual <= thr) else "🟡 NEAR" if (thr is not None and actual <= 1.2*thr) else "🟢 OK")
        src = f"{'SNAP' if csum.get('cycle_id') else 'DB'} / {lsrcs.get(sym, '—')}"
        rows.append([f"{icon} {sym} • 💧 Liquid", _fmt_num(actual), rule, _fmt_num(thr), result, src])

    add_liq("BTC","₿"); add_liq("ETH","Ξ"); add_liq("SOL","◎")

    # profit rows
    # compute actuals from snapshot/positions
    single_act = None; port_act = None
    try:
        cur = dl.db.get_cursor()
        if csum.get("cycle_id"):
            cur.execute("SELECT pnl_after_fees_usd FROM sonic_positions WHERE cycle_id=?", (csum["cycle_id"],))
        else:
            cur.execute("SELECT pnl_after_fees_usd FROM positions WHERE status='ACTIVE'")
        vals = [ _num(r[0],0.0) for r in (cur.fetchall() or []) if r and r[0] is not None ]
        pos = [v for v in vals if v > 0]
        single_act = max(pos) if pos else 0.0
        port_act   = sum(pos) if pos else 0.0
    except Exception:
        pass

    rows.append([
        "👤 Single • 💹 Profit",
        _fmt_usd(single_act),
        "≥",
        _fmt_usd(single_thr),
        "🟢 HIT" if (single_thr is not None and single_act is not None and single_act >= single_thr) else "· not met",
        f"{'SNAP' if csum.get('cycle_id') else 'DB'} / {psrcs.get('pos', '—')}",
    ])
    rows.append([
        "🧺 Portfolio • 💹 Profit",
        _fmt_usd(port_act),
        "≥",
        _fmt_usd(port_thr),
        "🟢 HIT" if (port_thr is not None and port_act is not None and port_act >= port_thr) else "· not met",
        f"{'SNAP' if csum.get('cycle_id') else 'DB'} / {psrcs.get('pf', '—')}",
    ])

    return rows, title_ts

def render(dl, csum: Dict[str, Any]) -> None:
    rows, title_ts = build_rows(dl, csum)
    # Keep only the column headers (per request to drop the standalone title row)
    headers = ["Metric", "Value", "Rule", "Threshold", "Result", "Source (V / T)"]
    write_table(None, headers, rows)
