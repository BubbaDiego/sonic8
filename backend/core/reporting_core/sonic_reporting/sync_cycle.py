# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, Optional, List

from .writer import write_table
from .state import once, set_resolved
from .config_probe import (
    discover_json_path,
    parse_json,
    schema_summary,
    resolve_effective,
)


def _ok(b: bool) -> str:
    return "✅" if b else "X"


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


def render(dl, csum: Dict[str, Any], default_json_path: str) -> None:
    """
    Render Sync Data as a compact table:

        Activity              | Status | Details
        ──────────────────────┼────────┼────────────────────────────────────────
        📦 Config JSON path   | ✅     | C:\...\sonic_monitor_config.json  [exists ✓, 995 bytes]
        🧪 Parse JSON         | ✅     | keys=(monitor, liquid, channels, profit, market, price)
        🔎 Schema check       | ✅     | liquid_monitor ✓, thresholds ✓, BTC ✓, ETH ✓, SOL ✓, profit_monitor ✗, pos ✗, pf ✗
        ↳ Normalized as       | ✅     | liquid_monitor.thresholds → BTC 5.3 • ETH 111.0 • SOL 8.0 ; profit_monitor → Single — • Portfolio —
        🧭 Read monitor thresholds | ✅ | JSON→DB→ENV
        💧 Liquid thresholds  | ✅     | BTC 5.3 • ETH 111 • SOL 8   [FILE]
        💹 Profit thresholds  | ✅     | Single $50 • Portfolio $200 [DB]

    Notes:
      - We cache the resolved (JSON-first) thresholds for this cycle via state.set_resolved.
      - We *exclude* mtime from the Config JSON path row per request.
    """

    # Discover + parse JSON
    json_path = discover_json_path(default_json_path)
    obj, err, meta = parse_json(json_path)

    # Build schema summary (for description row)
    summ = schema_summary(obj if isinstance(obj, dict) else None, dl)

    # JSON-first resolution for the rest of the cycle; store it
    resolved = resolve_effective(obj if isinstance(obj, dict) else None, dl)
    set_resolved(csum, resolved)

    # Build rows
    rows: List[List[str]] = []

    # 1) Config JSON path (no mtime)
    exists = bool(meta.get("exists"))
    size = meta.get("size", "—")
    rows.append([
        "📦 Config JSON path",
        _ok(exists),
        f"{json_path}  [exists {_chk(exists)}, {size} bytes]"
    ])

    # 2) Parse JSON
    if err:
        rows.append(["🧪 Parse JSON", _ok(False), f"error: {err}"])
    else:
        keys = ", ".join((obj or {}).keys()) if isinstance(obj, dict) else "—"
        rows.append(["🧪 Parse JSON", _ok(True), f"keys=({keys})"])

    # 3) Schema check
    lm = summ["normalized"].get("liquid_monitor", {}) or {}
    tm = (lm.get("thresholds") or {}) if isinstance(lm, dict) else {}
    btc_ok = "BTC" in tm
    eth_ok = "ETH" in tm
    sol_ok = "SOL" in tm
    pm = summ["normalized"].get("profit_monitor", {}) or {}
    pos_ok = "position_profit_usd" in pm
    pf_ok = "portfolio_profit_usd" in pm

    schema_all_ok = bool(lm) and bool(tm) and btc_ok and eth_ok and sol_ok and bool(pm) and pos_ok and pf_ok
    rows.append([
        "🔎 Schema check",
        _ok(schema_all_ok),
        f"liquid_monitor {_chk(bool(lm))}, thresholds {_chk(bool(tm))}, "
        f"BTC {_chk(btc_ok)}, ETH {_chk(eth_ok)}, SOL {_chk(sol_ok)}, "
        f"profit_monitor {_chk(bool(pm))}, pos {_chk(pos_ok)}, pf {_chk(pf_ok)}"
    ])

    # 4) Normalized as (show numbers; status = OK if we were able to compute *anything*)
    btc_v = _fmt_num(tm.get("BTC"))
    eth_v = _fmt_num(tm.get("ETH"))
    sol_v = _fmt_num(tm.get("SOL"))
    pos_v = pm.get("position_profit_usd")
    pf_v = pm.get("portfolio_profit_usd")
    norm_ok = any(v != "—" for v in (btc_v, eth_v, sol_v)) or (pos_v is not None or pf_v is not None)
    rows.append([
        "↳ Normalized as",
        _ok(norm_ok),
        f"liquid_monitor.thresholds → BTC {btc_v} • ETH {eth_v} • SOL {sol_v} ; "
        f"profit_monitor → Single {pos_v if pos_v is not None else '—'} • Portfolio {pf_v if pf_v is not None else '—'}"
    ])

    # 5) Resolved thresholds (JSON→DB→ENV)
    rows.append(["🧭 Read monitor thresholds", _ok(True), "JSON→DB→ENV"])

    # 6) Liquid thresholds (from resolved)
    lmap = resolved.get("liquid", {}) or {}
    lsrc = resolved.get("liquid_src", {}) or {}
    btc_r = _fmt_num(lmap.get("BTC"))
    eth_r = _fmt_num(lmap.get("ETH"))
    sol_r = _fmt_num(lmap.get("SOL"))
    # summarize sources
    uniq = {lsrc.get("BTC", "—"), lsrc.get("ETH", "—"), lsrc.get("SOL", "—")} - {"—"}
    src_display = "FILE" if uniq == {"FILE"} else ("DB" if uniq == {"DB"} else ("ENV" if uniq == {"ENV"} else f"MIXED(BTC={lsrc.get('BTC','—')}, ETH={lsrc.get('ETH','—')}, SOL={lsrc.get('SOL','—')})"))
    rows.append([
        "💧 Liquid thresholds",
        _ok(all(x != "—" for x in (btc_r, eth_r, sol_r))),
        f"BTC {btc_r} • ETH {eth_r} • SOL {sol_r}   [{src_display}]"
    ])

    # 7) Profit thresholds (from resolved)
    pmap = resolved.get("profit", {}) or {}
    psrc = resolved.get("profit_src", {}) or {}
    pos_r = pmap.get("pos")
    pf_r = pmap.get("pf")
    psrc_display = psrc.get("pos", "—") if psrc.get("pos") == psrc.get("pf") else f"MIXED(pos={psrc.get('pos','—')}, pf={psrc.get('pf','—')})"
    rows.append([
        "💹 Profit thresholds",
        _ok(pos_r is not None and pf_r is not None),
        f"Single ${int(pos_r) if pos_r is not None else '—'} • Portfolio ${int(pf_r) if pf_r is not None else '—'}   [{psrc_display}]"
    ])

    # Render as a single table (no title; sequencer prints the dashed header)
    write_table(
        title=None,
        headers=["Activity", "Status", "Details"],
        rows=rows
    )
