# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from typing import Dict, Any, Optional, List

from .writer import write_table, write_line
from .state import set_resolved
from .config_probe import (
    discover_json_path,
    parse_json,
    schema_summary,
    resolve_effective,
)

# Icons
ICON_BTC  = "🟡"
ICON_ETH  = "🔷"
ICON_SOL  = "🟣"
ICON_LIQ  = "💧"
ICON_PROF = "💹"
ICON_TOOL = "🛠️"

# ───────────────────────────────────────────────────────────────────────────────
# Helper formatting
# ───────────────────────────────────────────────────────────────────────────────

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

def _hdr_line(text: str) -> str:
    dash = "─" * 22
    icons = f"{ICON_TOOL} {ICON_TOOL} {ICON_TOOL}"
    return f"{dash} {icons}  {text}  {icons} {dash}"

# ───────────────────────────────────────────────────────────────────────────────
# Sync Activities collection
# ───────────────────────────────────────────────────────────────────────────────

_DUR_RE = re.compile(r"\((?P<secs>\d+(?:\.\d+)?)s\)")

def _truthy(val: Any) -> Optional[bool]:
    if isinstance(val, bool):
        return val
    if val is None:
        return None
    s = str(val).strip().lower()
    if s in ("1", "true", "ok", "success", "yes", "y", "✅"):
        return True
    if s in ("0", "false", "fail", "failed", "error", "err", "no", "n", "❌"):
        return False
    return None

def _fmt_dt(dt: Any) -> str:
    if dt is None or dt == "":
        return ""
    if isinstance(dt, (int, float)):
        return f"({dt:.2f}s)"
    s = str(dt).strip()
    return s if s.startswith("(") else f"({s})"

def _parse_log_line(line: str) -> Optional[Dict[str, Any]]:
    s = (line or "").strip()
    if not s or s.startswith(("INFO:", "WARNING:", "ERROR:")):
        return None
    m = _DUR_RE.search(s)
    duration: Optional[float] = None
    if m:
        try:
            duration = float(m.group("secs"))
        except Exception:
            duration = None
    ok: Optional[bool] = None
    if " ✅ " in s or s.endswith(" ✅"):
        ok = True
    elif "|ERROR" in s or " ERROR" in s or "❌" in s:
        ok = False
    note = s.split(" — ", 1)[1].strip() if " — " in s else ""
    label = _DUR_RE.sub("", s).replace("✅", "").replace("❌", "")
    label = " ".join(label.split()).lstrip("📈📥🧹🛡️📸📝📦⏭✅▶️🔊").strip()
    starters = (
        "Starting Price Sync", "Fetching positions", "Handle stale positions",
        "Generate hedges", "Snapshot portfolio", "Write sync report",
        "Sync summary", "price_monitor", "market_monitor",
        "profit_monitor", "liquid_monitor", "Twilio tts"
    )
    if not any(label.startswith(x) for x in starters):
        return None
    return {"label": label, "ok": ok, "duration": duration, "note": note}

def _merge_step(steps: List[Dict[str, Any]], step: Dict[str, Any]) -> None:
    lbl = str(step.get("label") or "").strip()
    if not lbl:
        return
    for s in steps:
        if str(s.get("label") or "").strip() == lbl:
            if s.get("ok") is None:
                s["ok"] = step.get("ok")
            if s.get("duration") in (None, "", 0):
                s["duration"] = step.get("duration")
            if not s.get("note"):
                s["note"] = step.get("note")
            return
    steps.append(step)

def _collect_activities(csum: Dict[str, Any]) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []

    # 1) lists: activities/steps/records/items/events
    for key in ("activities", "steps", "records", "items", "events"):
        v = csum.get(key)
        if isinstance(v, list):
            for it in v:
                if isinstance(it, dict):
                    _merge_step(steps, {
                        "label": it.get("label") or it.get("name") or it.get("step") or "—",
                        "ok": _truthy(it.get("ok") or it.get("status")),
                        "duration": it.get("duration") or it.get("dt"),
                        "note": it.get("note") or it.get("details") or it.get("extra") or "",
                    })
                elif isinstance(it, str):
                    p = _parse_log_line(it)
                    if p:
                        _merge_step(steps, p)

    # 2) raw log arrays too
    for lk in ("log", "logs", "log_lines"):
        lv = csum.get(lk)
        if isinstance(lv, list):
            for ln in lv:
                if isinstance(ln, str):
                    p = _parse_log_line(ln)
                    if p:
                        _merge_step(steps, p)

    # 3) known key fallback
    known = [
        ("Starting Price Sync",      "price_sync"),
        ("Fetching positions from Jupiter perps-api", "fetch_positions"),
        ("Handle stale positions",   "stale_positions"),
        ("Generate hedges",          "generate_hedges"),
        ("Snapshot portfolio",       "snapshot_portfolio"),
        ("Write sync report",        "write_sync_report"),
        ("price_monitor",            "price_monitor"),
        ("market_monitor",           "market_monitor"),
        ("profit_monitor",           "profit_monitor"),
        ("liquid_monitor",           "liquid_monitor"),
        ("Twilio tts",               "twilio_tts"),
    ]
    roots = [csum, csum.get("sync", {}), csum.get("summary", {}), csum.get("monitors", {})]
    for label, key in known:
        node: Dict[str, Any] = {}
        for r in roots:
            if isinstance(r, dict) and isinstance(r.get(key), dict):
                node = r[key]  # type: ignore
                break
        if node or any(k in csum for k in (f"{key}_ok", f"{key}_duration", f"{key}_dt")):
            ok = _truthy(node.get("ok", csum.get(f"{key}_ok")))
            dt = node.get("duration", csum.get(f"{key}_duration", csum.get(f"{key}_dt")))
            note = node.get("note") or node.get("details") or csum.get(f"{key}_note")
            _merge_step(steps, {"label": label, "ok": ok, "duration": dt, "note": note})

    # 4) aggregate “complete” row if stats exist
    stats = csum.get("stats") or csum.get("sync") or {}
    if isinstance(stats, dict) and any(k in stats for k in ("imported", "updated", "skipped", "errors")):
        imported = int(stats.get("imported", 0) or 0)
        updated  = int(stats.get("updated", 0) or 0)
        skipped  = int(stats.get("skipped", 0) or 0)
        errors   = int(stats.get("errors", 0) or 0)
        details  = f"{imported} imported, {updated} updated, {skipped} skipped, {errors} errors"
        _merge_step(steps, {"label": "Sync complete", "ok": (errors == 0), "duration": None, "note": details})

    # 5) if still empty, seed storyboard (neutral)
    if not steps:
        for s in [
            "Starting Price Sync", "Fetching positions from Jupiter perps-api",
            "Handle stale positions", "Generate hedges", "Snapshot portfolio", "Write sync report"
        ]:
            steps.append({"label": s, "ok": None, "duration": None, "note": ""})

    return steps

# ───────────────────────────────────────────────────────────────────────────────
# Public render — prints BOTH sections in order (Activities, then Data)
# ───────────────────────────────────────────────────────────────────────────────

def render(dl, csum: Dict[str, Any], default_json_path: str) -> None:
    """
    Print 'Sync Activities' (3-col table), then 'Sync Data' (baseline 3-col table).
    Titles are printed here so sequencer should NOT print its own Sync Data title.
    """
    # ---- Sync Activities ----
    write_line("")  # single spacer from previous block
    write_line(_hdr_line("Sync  Activities"))
    act_headers = ["Activity", "Status", "Details"]
    act_rows: List[List[str]] = []
    for step in _collect_activities(csum):
        label = str(step.get("label") or "—")
        ok = _truthy(step.get("ok"))
        status = "✅" if ok is True else ("❌" if ok is False else "·")
        dt = step.get("duration")
        dt_txt = _fmt_dt(dt) if dt not in (None, "", 0) else ""
        note = step.get("note") or ""
        details = f"{dt_txt} — {note}".strip(" —")
        act_rows.append([label, status, details])
    write_table(None, act_headers, act_rows)

    # ---- Sync Data (baseline restored) ----
    write_line("")
    write_line(_hdr_line("Sync  Data"))

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
    if   uniq == {"FILE"}: src_display = "FILE"
    elif uniq == {"DB"}:   src_display = "DB"
    elif uniq == {"ENV"}:  src_display = "ENV"
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

    write_table(title=None, headers=["Activity", "Status", "Details"], rows=rows)
