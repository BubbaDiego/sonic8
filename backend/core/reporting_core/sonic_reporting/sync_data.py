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
ICON_SINGLE = "👤"
ICON_PF = "🧺"

# Nudge the whole table a bit to the right of the title line
LEFT_PAD = "  "  # two spaces

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

def _indent_block(text: str, indent: str = "  ") -> str:
    """Indent every line of a multi-line string except the first; no trailing blank line."""
    lines = text.splitlines()
    if not lines:
        return ""
    return "\n".join([lines[0]] + [indent + line for line in lines[1:]])

def render(dl, csum: Dict[str, Any], default_json_path: str) -> None:
    """
    Print ONLY the Sync Data table (no dashed title, no extra spacers).
    - No blank line after 'Schema check'
    - Table content shifted slightly right via LEFT_PAD
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

    # Build the table rows (Activity column is padded)
    rows: List[List[str]] = []

    # Config JSON path (no mtime) — path only (no keys here)
    rows.append([
        f"{LEFT_PAD}📦 Config JSON path",
        _ok(exists),
        f"{json_path}"
    ])

    # Parse JSON — include keys listing here (single place)
    if err:
        rows.append([f"{LEFT_PAD}🧪 Parse JSON", _ok(False), f"error: {err}"])
    else:
        keys = ", ".join((obj or {}).keys()) if isinstance(obj, dict) else "—"
        rows.append([f"{LEFT_PAD}🧪 Parse JSON", _ok(True), f"keys=({keys})"])

    # Schema check — split across two lines, no blank spacer afterwards
    lm = summ["normalized"].get("liquid_monitor", {}) or {}
    tm = (lm.get("thresholds") or {}) if isinstance(lm, dict) else {}
    btc_ok = "BTC" in tm
    eth_ok = "ETH" in tm
    sol_ok = "SOL" in tm
    pm = summ["normalized"].get("profit_monitor", {}) or {}
    pos_ok = "position_profit_usd" in pm
    pf_ok  = "portfolio_profit_usd" in pm

    schema_all_ok = bool(lm) and bool(tm) and btc_ok and eth_ok and sol_ok and bool(pm) and pos_ok and pf_ok
    schema_line1 = f"{ICON_LIQ}mon {_chk(bool(lm))} · thr {_chk(bool(tm))}"
    schema_line2 = (
        f"{ICON_BTC}BTC {_chk(btc_ok)} · {ICON_ETH}ETH {_chk(eth_ok)} · "
        f"{ICON_SOL}SOL {_chk(sol_ok)} · {ICON_PROF}mon {_chk(bool(pm))} · "
        f"pos {_chk(pos_ok)} · pf {_chk(pf_ok)}"
    )
    schema_details = _indent_block(f"{schema_line1}\n{schema_line2}", indent="  ")
    rows.append([f"{LEFT_PAD}🔎 Schema check", _ok(schema_all_ok), schema_details])

    # Resolved (JSON→DB→ENV) summary (single line)
    rows.append([f"{LEFT_PAD}🧭 Read monitor thresholds", _ok(True), "JSON→DB→ENV"])

    # Liquid thresholds — multi-line, indented under Details
    lmap = resolved.get("liquid", {}) or {}
    lsrc = resolved.get("liquid_src", {}) or {}
    btc_r = _fmt_num(lmap.get("BTC"))
    eth_r = _fmt_num(lmap.get("ETH"))
    sol_r = _fmt_num(lmap.get("SOL"))
    liquid_block = _indent_block(
        "Monitor:\n"
        f"{ICON_BTC} BTC {btc_r} ({lsrc.get('BTC','—')})\n"
        f"{ICON_ETH} ETH {eth_r} ({lsrc.get('ETH','—')})\n"
        f"{ICON_SOL} SOL {sol_r} ({lsrc.get('SOL','—')})",
        indent="  "
    )
    rows.append([
        f"{LEFT_PAD}{ICON_LIQ} Liquid thresholds",
        _ok(all(x != "—" for x in (btc_r, eth_r, sol_r))),
        liquid_block
    ])

    # Profit thresholds — multi-line, indented under Details
    pmap = resolved.get("profit", {}) or {}
    psrc = resolved.get("profit_src", {}) or {}
    pos_r = pmap.get("pos")
    pf_r  = pmap.get("pf")
    profit_block = _indent_block(
        "Monitor:\n"
        f"{ICON_SINGLE} Single ${int(pos_r) if pos_r is not None else '—'} ({psrc.get('pos','—')})\n"
        f"{ICON_PF} Portfolio ${int(pf_r) if pf_r is not None else '—'} ({psrc.get('pf','—')})",
        indent="  "
    )
    rows.append([
        f"{LEFT_PAD}{ICON_PROF} Profit thresholds",
        _ok(pos_r is not None and pf_r is not None),
        profit_block
    ])

    # Render table (sequencer prints the dashed title)
    headers = [f"{LEFT_PAD}Activity", "Status", "Details"]
    write_table(title=None, headers=headers, rows=rows)
