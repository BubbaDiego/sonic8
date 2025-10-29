# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any
from .writer import write_line
from .styles import ICON_SUMMARY, ICON_SEARCH, ICON_EVAL
from .state import once, set_resolved
from .config_probe import discover_json_path, parse_json, schema_summary, resolve_effective

def render(dl, csum: Dict[str, Any], default_json_path: str) -> None:
    # Ensure the sync details print only once per cycle
    if not once("sync_block", csum):
        return

    # JSON probe
    json_path = discover_json_path(default_json_path)
    obj, err, meta = parse_json(json_path)
    write_line(f"{ICON_SUMMARY} Config JSON path  : {json_path}  " + (f"[exists ✓, {meta['size']} bytes, mtime {meta['mtime']}]" if meta["exists"] else "[missing ✗]"))
    if err:
        write_line(f"{ICON_SEARCH} Parse JSON        : ❌ {err}")
    else:
        keys = ", ".join(obj.keys()) if isinstance(obj, dict) else "—"
        write_line(f"{ICON_SEARCH} Parse JSON        : ✅ keys=({keys})")

    # Schema
    summ = schema_summary(obj if isinstance(obj, dict) else None, dl)
    flags = []
    lm = summ["normalized"].get("liquid_monitor", {})
    tm = lm.get("thresholds") or {}
    flags.append("liquid_monitor " + ("✓" if lm else "✗"))
    flags.append("thresholds " + ("✓" if tm else "✗"))
    for s in ("BTC","ETH","SOL"):
        flags.append(f"{s} " + ("✓" if s in tm else "✗"))
    pm = summ["normalized"].get("profit_monitor", {})
    flags.append("profit_monitor " + ("✓" if pm else "✗"))
    flags.append("pos " + ("✓" if "position_profit_usd" in pm else "✗"))
    flags.append("pf "  + ("✓" if "portfolio_profit_usd" in pm else "✗"))
    write_line("🔎 Schema check      : " + ", ".join(flags))

    # Normalized summary (legacy -> modern)
    btc, eth, sol = tm.get("BTC"), tm.get("ETH"), tm.get("SOL")
    pos, pf = pm.get("position_profit_usd"), pm.get("portfolio_profit_usd")
    write_line(f"↳ Normalized as     : liquid_monitor.thresholds → BTC {btc} • ETH {eth} • SOL {sol} ; "
               f"profit_monitor → Single {pos if pos is not None else '—'} • Portfolio {pf if pf is not None else '—'}")

    # JSON-first resolution used everywhere downstream in this cycle
    resolved = resolve_effective(obj if isinstance(obj, dict) else None, dl)
    set_resolved(csum, resolved)

    # Print effective thresholds from resolved
    def _fmt(v):
        try:
            return f"{float(v):.2f}".rstrip("0").rstrip(".") if v is not None else "—"
        except Exception:
            return "—"

    # Liquid line with sources summary
    l = resolved["liquid"]
    ls = resolved["liquid_src"]
    uniq = {ls["BTC"], ls["ETH"], ls["SOL"]} - {"—"}
    src_display = (
        "FILE" if uniq == {"FILE"} else (
            "DB" if uniq == {"DB"} else f"MIXED(BTC={ls['BTC']}, ETH={ls['ETH']}, SOL={ls['SOL']})"
        )
    )
    write_line(f"{ICON_EVAL} Read monitor thresholds  ✅ (0.00s)")
    write_line(
        f"💧 Liquid thresholds : BTC {_fmt(l['BTC'])} • ETH {_fmt(l['ETH'])} • SOL {_fmt(l['SOL'])}   [{src_display}]"
    )

    # Profit line with source(s)
    p = resolved["profit"]
    ps = resolved["profit_src"]
    puniq = {ps["pos"], ps["pf"]} - {"—"}
    psrc = list(puniq)[0] if len(puniq) == 1 else f"MIXED(pos={ps['pos']}, pf={ps['pf']})"
    write_line(
        f"💹 Profit thresholds : Single ${int(p['pos']) if p['pos'] is not None else '—'} • Portfolio ${int(p['pf']) if p['pf'] is not None else '—'}   [{psrc}]"
    )
