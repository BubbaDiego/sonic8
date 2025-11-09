# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import json
import os, unicodedata

# standardized title via console_panels.theming
from .console_panels.theming import (
    console_width as _theme_width,
    hr as _theme_hr,
    title_lines as _theme_title,
)
PANEL_SLUG = "xcom"
PANEL_NAME = "XCom"

# ===== colors (title text only; bars remain plain) =====
USE_COLOR   = os.getenv("SONIC_COLOR", "1").strip().lower() not in {"0","false","no","off"}
TITLE_COLOR = os.getenv("SONIC_TITLE_COLOR", "\x1b[38;5;45m")
def _c(s: str, color: str) -> str: return f"{color}{s}\x1b[0m" if USE_COLOR else s

# ===== layout =====
HR_WIDTH = 78
INDENT   = "  "
# icon + 6 tight columns
W_ICON, W_CH, W_DIR, W_TYPE, W_PEER, W_ST, W_AGE, W_SRC = 3, 10, 4, 8, 26, 9, 6, 8
SEP = " "

# emoji-safe padding helpers
_VAR={0xFE0F,0xFE0E}; _ZW={0x200D,0x200C}
def _dl(s: str) -> int:
    t=0
    for ch in s or "":
        cp=ord(ch)
        if cp in _VAR or cp in _ZW: continue
        ew=unicodedata.east_asian_width(ch)
        t += 2 if ew in ("W","F") else 1
    return t
def _pad(s: Any, w: int, *, right=False) -> str:
    t = "" if s is None else str(s)
    L = _dl(t)
    if L >= w:
        while t and _dl(t) > w: t = t[:-1]
        return t
    pad = " "*(w-L)
    return (pad+t) if right else (t+pad)
def _pad_center(s: Any, w: int) -> str:
    t = "" if s is None else str(s)
    L = _dl(t)
    if L >= w:
        while t and _dl(t) > w: t=t[:-1]
        return t
    total=w-L; left=total//2; right=total-left
    return (" "*left) + t + (" "*right)

# icons
PROV_ICON = {
    "twilio":"📞", "textbelt":"✉️", "webhook":"🪝", "smtp":"✉️",
    "email":"✉️", "push":"📣", "custom":"📡",
}
STATE_ICON = {"OK":"✅","WARN":"⚠︎","BREACH":"🔥","SNOOZE":"🔕", "QUEUED":"⌛", "SENT":"✅", "DELIVERED":"✅", "RECEIPT":"✅", "FAILED":"✖️", "RECEIVED":"✅", "PROCESSED":"✅", "PENDING":"⌛"}

def _abbr_peer(s: Any) -> str:
    txt = "" if s is None else str(s)
    if not txt: return "—"
    return txt if len(txt) <= 18 else (txt[:14] + "…"+ txt[-3:])

def _fmt_state(st: str) -> str:
    key = (st or "").upper()
    icon = STATE_ICON.get(key, "•")
    return f"{icon} {key}"

def _fmt_age(ts: Any) -> str:
    if not ts: return "—"
    try:
        if isinstance(ts,(int,float)):
            dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(ts).replace("Z","+00:00"))
        d=(datetime.now(timezone.utc) - dt).total_seconds()
        if d < 0: d = 0
        return f"{int(d)}s" if d < 90 else (f"{int(d//60)}m" if d < 5400 else f"{int(d//3600)}h")
    except: return "—"

# data access
def _latest_rows_via_manager(dl: Any) -> Optional[List[Dict[str,Any]]]:
    try:
        xm = getattr(dl, "xcom", None)
        if xm is not None:
            return xm.latest(limit=30)
    except: pass
    return None

def _load_from_table(dl: Any) -> List[Dict[str,Any]]:
    try:
        cur = dl.db.get_cursor()
        # prefer xcom_messages
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='xcom_messages'")
        if not cur.fetchone(): return []
        cur.execute(
            "SELECT ts, provider, direction, message_type, to_addr, from_addr, endpoint, status, source, meta "
            "FROM xcom_messages ORDER BY ts DESC LIMIT 30"
        )
        cols=[c[0] for c in cur.description]
        out=[dict(zip(cols,row)) for row in cur.fetchall()]
        for d in out:
            if isinstance(d.get("meta"), str):
                try: d["meta"] = json.loads(d["meta"])
                except: d["meta"] = {}
            elif d.get("meta") is None:
                d["meta"] = {}
        return out
    except: return []

def _latest_rows(dl: Any) -> List[Dict[str,Any]]:
    rs = _latest_rows_via_manager(dl)
    if rs: return rs
    return _load_from_table(dl)

def _norm(d: Dict[str,Any]) -> Dict[str,Any]:
    prov = (d.get("provider") or "custom").lower()
    di   = (d.get("direction") or "OUT").upper()
    mtyp = (d.get("message_type") or "other").lower()
    status = (d.get("status") or "PENDING").upper()
    # decide peer (to/from/endpoint)
    peer = d.get("to_addr") if di == "OUT" else d.get("from_addr")
    if not peer:
        peer = d.get("endpoint")
    return {
        "provider": prov,
        "direction": di,
        "type": mtyp,
        "peer": peer,
        "status": status,
        "ts": d.get("ts"),
        "source": d.get("source") or prov,
    }

# render
def render(dl, *_args, **_kw) -> None:
    raw = _latest_rows(dl)
    rows = [_norm(r) for r in raw]

    width = _theme_width()
    print()
    print(_theme_hr(width))
    for ln in _theme_title(PANEL_SLUG, PANEL_NAME, width=width):
        print(ln)
    print(_theme_hr(width))

    # Header (icons + text; no row coloring)
    print(
        INDENT
        + _pad("", W_ICON)
        + _pad("📡 Chan", W_CH)
        + SEP + _pad("⇄ Dir",   W_DIR)
        + SEP + _pad("🧾 Type", W_TYPE)
        + SEP + _pad("👤 To/From", W_PEER)
        + SEP + _pad_center("🧮 State", W_ST)
        + SEP + _pad("⏱ Age", W_AGE, right=True)
        + SEP + _pad("🪪 Source", W_SRC)
    )
    print(INDENT + "─"*HR_WIDTH)

    if not rows:
        print(f"{INDENT}(no xcom messages)")
        print()
        return

    # print latest up to 30
    for r in rows[:30]:
        icon = PROV_ICON.get(r["provider"], "📡") + " "
        chan = r["provider"]
        dire = "⇢" if r["direction"] == "OUT" else "⇠"
        typ  = r["type"]
        peer = _abbr_peer(r["peer"])
        stxt = _fmt_state(r["status"])
        age  = _fmt_age(r["ts"])
        src  = r["source"]

        print(
            INDENT
            + _pad(icon, W_ICON)
            + _pad(chan, W_CH)
            + SEP + _pad(dire, W_DIR)
            + SEP + _pad(typ,  W_TYPE)
            + SEP + _pad(peer, W_PEER)
            + SEP + _pad_center(stxt, W_ST)
            + SEP + _pad(age,  W_AGE, right=True)
            + SEP + _pad(src,  W_SRC)
        )
    print()
