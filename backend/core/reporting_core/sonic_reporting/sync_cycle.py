# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, Optional, List

from .writer import write_table
from .state import set_resolved
from .config_probe import (
    discover_json_path,
    parse_json,
    schema_summary,
    resolve_effective,
)

# Asset / monitor icons
ICON_BTC = "🟡"
ICON_ETH = "🔷"
ICON_SOL = "🟣"
ICON_LIQ = "💧"
ICON_PROF = "💹"

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


def render(dl, csum: Dict[str, Any], default_json_path: str) -> None:
    """
    Render Sync Data as a compact table:

      Activity                | Status | Details
      ------------------------+--------+-----------------------------------------
      📦 Config JSON path     |  ✅    | C:\...\sonic_monitor_config.json  [exists ✓, 995 bytes]
      🧪 Parse JSON           |  ✅    | keys=(monitor, liquid, channels, profit, market, price)
      🔎 Schema check         |  ✅/❌  | 💧mon ✓ · thr ✓ · 🟡BTC ✓ · 🔷ETH ✓ · 🟣SOL ✓ · 💹mon ✗ · pos ✗ · pf ✗
      ↳ Normalized as         |  ✅/❌  | → 💧 BTC 5.30 • ETH 111.0 • SOL 8.0 ; 💹 Single — • Portfolio —
      🧭 Read monitor thresholds | ✅  | JSON→DB→ENV
      💧 Liquid thresholds    |  ✅/❌  | 🟡 5.3 • 🔷 111 • 🟣 8   [FILE|DB|ENV|MIXED(...)]
      💹 Profit thresholds    |  ✅/❌  | Single $50 • Portfolio $200   [DB|FILE|ENV|MIXED(...)]
    """

    # 1) Discover + parse JSON (no mtime shown)
    json_path = discover_json_path(default_json_path)
    obj, err, meta = parse_json(json_path)
    exists = bool(meta.get("exists"))
    size = meta.get("size", "—")

    # 2) Schema summary for the compact row
    summ = schema_summary(obj if isinstance(obj, dict) else None, dl)

    # 3) JSON-first effective thresholds (and cache for this cycle)
    resolved = resolve_effective(obj if isinstance(obj, dict) else None, dl)
    set_resolved(csum, resolved)

    # Build the table rows
    rows: List[List[str]] = []

    # Config JSON path (no mtime)
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
        f"{ICON_LIQ}mon {_chk(bool(lm))} · thr {_chk(bool(tm))} · "
        f"{ICON_BTC}BTC {_chk(btc_ok)} · {ICON_ETH}ETH {_chk(eth_ok)} · {ICON_SOL}SOL {_chk(sol_ok)} · "
        f"{ICON_PROF}mon {_chk(bool(pm))} · pos {_chk(pos_ok)} · pf {_chk(pf_ok)}"
    )
    rows.append(["🔎 Schema check", _ok(schema_all_ok), schema_details])

    # Normalized as — compact with icons
    btc_v = _fmt_num(tm.get("BTC"))
    eth_v = _fmt_num(tm.get("ETH"))
    sol_v = _fmt_num(tm.get("SOL"))
    pos_v = pm.get("position_profit_usd")
    pf_v  = pm.get("portfolio_profit_usd")
    norm_ok = any(v != "—" for v in (btc_v, eth_v, sol_v)) or (pos_v is not None or pf_v is not None)
    norm_details = (
        f"→ {ICON_LIQ} {ICON_BTC} {btc_v} • {ICON_ETH} {eth_v} • {ICON_SOL} {sol_v} ; "
        f"{ICON_PROF} Single {pos_v if pos_v is not None else '—'} • Portfolio {pf_v if pf_v is not None else '—'}"
    )
    rows.append(["↳ Normalized as", _ok(norm_ok), norm_details])

    # Resolved (JSON→DB→ENV) summary and effective numbers
    rows.append(["🧭 Read monitor thresholds", _ok(True), "JSON→DB→ENV"])

    lmap = resolved.get("liquid", {}) or {}
    lsrc = resolved.get("liquid_src", {}) or {}
    btc_r = _fmt_num(lmap.get("BTC"))
    eth_r = _fmt_num(lmap.get("ETH"))
    sol_r = _fmt_num(lmap.get("SOL"))

    uniq = {lsrc.get("BTC", "—"), lsrc.get("ETH", "—"), lsrc.get("SOL", "—")} - {"—"}
    if uniq == {"FILE"}:
        src_display = "FILE"
    elif uniq == {"DB"}:
        src_display = "DB"
    elif uniq == {"ENV"}:
        src_display = "ENV"
    else:
        src_display = f"MIXED(BTC={lsrc.get('BTC','—')}, ETH={lsrc.get('ETH','—')}, SOL={lsrc.get('SOL','—')})"

    rows.append([
        f"{ICON_LIQ} Liquid thresholds",
        _ok(all(x != "—" for x in (btc_r, eth_r, sol_r))),
        f"{ICON_BTC} {btc_r} • {ICON_ETH} {eth_r} • {ICON_SOL} {sol_r}   [{src_display}]"
    ])

    pmap = resolved.get("profit", {}) or {}
    psrc = resolved.get("profit_src", {}) or {}
    pos_r = pmap.get("pos")
    pf_r  = pmap.get("pf")
    puniq = {psrc.get("pos", "—"), psrc.get("pf", "—")} - {"—"}
    psrc_display = list(puniq)[0] if len(puniq) == 1 else f"MIXED(pos={psrc.get('pos','—')}, pf={psrc.get('pf','—')})"

    rows.append([
        f"{ICON_PROF} Profit thresholds",
        _ok(pos_r is not None and pf_r is not None),
        f"Single ${int(pos_r) if pos_r is not None else '—'} • Portfolio ${int(pf_r) if pf_r is not None else '—'}   [{psrc_display}]"
    ])

    # Render table (sequencer provides the dashed section header)
    write_table(
        title=None,
        headers=["Activity", "Status", "Details"],
        rows=rows
    )
