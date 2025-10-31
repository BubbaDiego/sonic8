# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from typing import Dict, Any, Optional, List

from .writer import write_table

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

def render(dl, csum: Dict[str, Any]) -> None:
    """
    Print ONLY the Sync Activities table.
    - No dashed title, no leading/trailing blank line.
    - Column headers are part of the table (colored by writer/styles).
    """
    headers = ["Activity", "Status", "Details"]
    rows: List[List[str]] = []
    for step in _collect_activities(csum):
        label = str(step.get("label") or "—")
        ok = _truthy(step.get("ok"))
        status = "✅" if ok is True else ("❌" if ok is False else "·")
        dt = step.get("duration")
        dt_txt = _fmt_dt(dt) if dt not in (None, "", 0) else ""
        note = step.get("note") or ""
        details = f"{dt_txt} — {note}".strip(" —")
        rows.append([label, status, details])
    write_table(None, headers, rows)
