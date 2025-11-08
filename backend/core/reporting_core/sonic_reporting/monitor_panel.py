# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
import json
import unicodedata
import os

# ============================================================
# CONFIG: colors (only title text is colored; bars remain plain)
USE_COLOR   = os.getenv("SONIC_COLOR", "1").strip().lower() not in {"0", "false", "no", "off"}
TITLE_COLOR = os.getenv("SONIC_TITLE_COLOR", "\x1b[38;5;45m")   # cyan/teal
def _c(s: str, color: str) -> str:
    return f"{color}{s}\x1b[0m" if USE_COLOR else s
# ============================================================

# ====== Layout ======
HR_WIDTH = 78
INDENT   = "  "

# Compact column widths (sum + 5 separators ≈ 78 - len(INDENT))
W_MON  = 22   # "💧 BTC – Liq"
W_TH   = 10   # "≤ 1.0%"
W_VAL  = 10   # "$12.3" / "1.2%" / "12 bp"
W_ST   = 9    # "✅ OK" / "⚠︎ WARN" / "🔥 BREACH" / "🔕 SNOOZE"
W_AGE  = 6    # "12s" / "3m" / "1h"
W_SRC  = 5    # "liq"/"profit"/"mkt"/"feed"
SEP    = "  "

HEADER_IC = {
    "mon":  "🎛",
    "thr":  "🎯",
    "val":  "💡",
    "st":   "🧮",
    "age":  "⏱",
    "src":  "🪪",
}

SEVERITY_RANK = {"BREACH": 0, "SNOOZE": 1, "WARN": 2, "OK": 3}
MON_RANK      = {"liquid": 0, "profit": 1, "market": 2, "custom": 3}

STATE_ICON = {
    "OK":     "✅",
    "WARN":   "⚠︎",
    "BREACH": "🔥",
    "SNOOZE": "🔕",
}

MON_ICON = {
    "liquid": "💧",
    "profit": "💹",
    "market": "📈",
    "custom": "🧪",
}

# ====== Emoji-aware padding (same approach as Positions panel) ======
_VARIATION_SELECTORS = {0xFE0F, 0xFE0E}
_ZERO_WIDTH = {0x200D, 0x200C}

def _disp_len(s: str) -> int:
    total = 0
    for ch in s:
        cp = ord(ch)
        if cp in _VARIATION_SELECTORS or cp in _ZERO_WIDTH:
            continue
        ew = unicodedata.east_asian_width(ch)
        total += 2 if ew in ("W", "F") else 1
    return total

def _padw(text: Any, width: int, *, right: bool = False) -> str:
    s = "" if text is null_or_empty(text) else str(text)
    cur = _disp_len(s)
    if cur >= width:
        # trim down to fit
        while s and _disp_len(s) > width:
            s = s[:-1]
        return s
    pad = " " * (width - cur)
    return (pad + s) if right else (s + pad)

def _pad(s: Any, w: int, right: bool = False) -> str:
    return _padw(s, w, right=right)

def null_or_empty(x: Any) -> bool:
    return x is None or (isinstance(x, str) and x == "")

# ====== Title rule ======
def _hr(title: str) -> str:
    plain = f"  {title} "            # used for width calc
    colored = f" {_c('🔎  ' + title, TITLE_COLOR)} "
    pad = HR_WIDTH - len(plain)
    if pad < 0:
        pad = 0
    L = pad // 2
    R = pad - L
    return INDENT + "─" * L + colored + "─" * R

# ====== Formatting helpers ======
def _fmt_threshold(meta: Dict[str, Any]) -> str:
    try:
        thr = meta.get("threshold") or {}
        op   = thr.get("op") or thr.get("operator") or ""
        val  = thr.get("value")
        unit = thr.get("unit") or ""
        if val is None:
            return "—"
        symbol = {"<": "＜", "<=": "≤", ">": "＞", ">=": "≥", "==": "＝"}.get(op, str(op) or "")
        val_str = _fmt_metric(val, unit)
        return f"{symbol} {val_str}".strip() if symbol else val_str
    except Exception:
        return "—"

def _fmt_metric(value: Any, unit: str) -> str:
    try:
        v = float(value)
    except Exception:
        return "—"
    u = (unit or "").strip().lower()
    if u in {"$", "usd", "usdt", "usdc"}:
        if abs(v) >= 1_000_000:
            return f"${v/1_000_000:.1f}m".replace(".0m", "m")
        if abs(v) >= 1_000:
            return f"${v/1_000:.1f}k".replace(".0k", "k")
        return f"${v:,.2f}"
    if u in {"%", "pct", "percent"}:
        return f"{v:.2f}%"
    if u in {"bp", "bps"}:
        return f"{v:.0f}bp"
    # no unit or unknown -> plain number
    return f"{v:.4g}"

def _fmt_state(st: str) -> str:
    s = (st or "").upper()
    icon = STATE_ICON.get(s, "·")
    label = s if s in STATE_ICON else (s or "—")
    return f"{icon} {label}"

def _fmt_age(ts: Optional[str]) -> str:
    if not ts:
        return "—"
    try:
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
        else:
            t = str(ts)
            dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
        delta = (datetime.now(timezone.utc) - dt).totalSeconds()
        if delta < 0: delta = 0
        if delta < 90:
            return f"{int(delta)}s"
        if delta < 5400:
            return f"{int(delta // 60)}m"
        return f"{int(delta // 3600)}h"
    except Exception:
        return "—"

# ====== Data access ======
def _latest_rows(dl: Any) -> Tuple[List[Dict[str, Any]], str]:
    try:
        cur = dl.db.get_cursor()
        cur.execute("SELECT MAX(cycle_id) FROM monitor_status")
        row = cur.fetchone()
        if not row or not row[0]:
            return [], "db.monitor_status"
        cycle_id = row[0]
        cur.execute(
            "SELECT monitor, label, state, value, unit, meta FROM monitor_status WHERE cycle_id = ?",
            (cycle_id,)
        )
        cols = [c[0] for c in cur.description]
        out = [dict(zip(cols, r)) for r in cur.fetchall()]
        return out, "db.monitor_status"
    except Exception:
        return [], "db.monitor_status"

# ====== Normalize & sort ======
def _normalize_row(r: Dict[str, Any]) -> Dict[str, Any]:
    meta = r.get("meta")
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}
    elif meta is None:
        meta = {}
    # ts can live in meta under various keys
    ts = meta.get("ts") or meta.get("timestamp") or meta.get("updated_at") or meta.get("time") or meta.get("at")
    return {
        "monitor": (r.get("monitor") or "custom").lower(),
        "label":   r.get("label") or "",
        "state":   (r.get("state") or "OK").upper(),
        "value":   r.get("value"),
        "unit":    r.get("unit") or meta.get("unit") or "",
        "meta":    meta,
        "ts":      ts,
        "source":  meta.get("source") or (r.get("monitor") or "")[:6],
    }

def _sort_key(row: Dict[str, Any]) -> Tuple[int, int, str]:
    sev = SEVERITY_RANK.get(row["state"], 4)
    grp = MON_RANK.get(row["monitor"], 9)
    return (sev, grp, str(row["label"]))

# ====== Render ======
def render(dl, *_args, **_kw) -> None:
    raw, source = _latest_rows(dl)
    rows = [_normalize_row(r) for r in raw]
    rows.sort(key=_sort_key)

    print()
    print(_hr("Monitors"))
    header = (
        INDENT
        + _pad(HEADER_IC["mon"] + "Mon",  W_MON)
        + SEP + _pad(HEADER_IC["thr"] + "Thresh", W_TH)
        + SEP + _pad(HEADER_IC["val"] + "Value",  W_VAL)
        + SEP + _pad(HEADER_IC["st"]  + "State",  W_ST)
        + SEP + _pad(HEADER_IC["age"] + "Age",    W_AGE, right=True)
        + SEP + _pad(HEADER_IC["src"] + "Src",    W_SRC)
    )
    print(header)
    print(INDENT + "─" * HR_WIDTH)

    if not rows:
        print(f"{INDENT}[MON] source: {source} (0 rows)")
        print(f"{INDENT}(no monitor results)")
        print()  # breathing room
        return

    for r in rows:
        icon  = MON_ICON.get(r["monitor"], "🧪")
        mon   = f"{icon} {r['label'] or r['monitor'].title()}"
        thr   = _fmt_threshold(r["meta"])
        val   = _fmt_metric(r["value"], r["unit"])
        state = _fmt_state(r["state"])
        age   = _fmt_age(r["ts"])
        src   = (r["source"] or r["monitor"])[:W_SRC]

        line = (
            INDENT
            + _pad(mon,  W_MON)
            + SEP + _pad(thr,  W_TH)
            + SEP + _pad(val,  W_VAL, right=True)
            + SEP + _pad(state, W_ST)
            + SEP + _pad(age,  W_AGE, right=True)
            + SEP + _pad(src,  W_SRC)
        )
        print(line)

    # Summary footer
    n_ok   = sum(1 for r in rows if r["state"] == "OK")
    n_warn = sum(1 for r in rows if r["state"] == "WARN")
    n_snz  = sum(1 for r in rows if r["state"] == "SNOOZE")
    n_br   = sum(1 for r in rows if r["state"] == "BREACH")
    # latest age among rows
    ages = [ _fmt_age(r["ts"]) for r in rows if r.get("ts") ]
    last_age = ages[0] if ages else "—"

    summary = (
        f"Summary:  {STATE_ICON['OK']} {n_ok}   "
        f"{STATE_ICON['WARN']} {n_warn}   "
        f"{STATE_ICON['SNOOZE']} {n_snz}   "
        f"{STATE_ICON['BREACH']} {n_br}    last update {last_age}"
    )
    # keep the footer in plain text (no extra color), same width as header bar
    print(INDENT + summary)
    print()  # one blank line after panel
