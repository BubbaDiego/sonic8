# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
import json, unicodedata, os

# ===== colors =====
USE_COLOR   = os.getenv("SONIC_COLOR", "1").strip().lower() not in {"0","false","no","off"}
TITLE_COLOR = os.getenv("SONIC_TITLE_COLOR", "\x1b[38;5;45m")
def _c(s: str, color: str) -> str: return f"{color}{s}\x1b[0m" if USE_COLOR else s

# ===== layout =====
HR_WIDTH = 78
INDENT   = "  "
W_MON, W_TH, W_VAL, W_ST, W_AGE, W_SRC = 22, 10, 10, 9, 6, 5
SEP = "  "
HEADER_IC = {"mon":"🎛","thr":"🎯","val":"💡","st":"🧮","age":"⏱","src":"🪪"}

STATE_ICON = {"OK":"✅","WARN":"⚠︎","BREACH":"🔥","SNOOZE":"🔕"}
MON_ICON   = {"liquid":"💧","profit":"💹","market":"📈","custom":"🧪"}
SEVERITY_RANK = {"BREACH":0,"SNOOZE":1,"WARN":2,"OK":3}
MON_RANK      = {"liquid":0,"profit":1,"market":2,"custom":3}

# ===== emoji-safe padding =====
_VAR={0xFE0F,0xFE0E}; _ZW={0x200D,0x200C}
def _dl(s: str) -> int:
    tot=0
    for ch in s or "":
        cp=ord(ch)
        if cp in _VAR or cp in _ZW: continue
        ew=unicodedata.east_asian_width(ch)
        tot += 2 if ew in ("W","F") else 1
    return tot
def _pad(s: Any, w: int, *, right=False) -> str:
    t = "" if s is None else str(s)
    L = _dl(t)
    if L >= w:
        while t and _dl(t) > w: t = t[:-1]
        return t
    pad = " " * (w - L)
    return (pad + t) if right else (t + pad)

# ===== helpers =====
def _hr(title: str) -> str:
    plain = f"  {title} "
    col   = f" {_c('🔎  ' + title, TITLE_COLOR)} "
    pad = HR_WIDTH - len(plain)
    if pad < 0: pad = 0
    L = pad // 2; R = pad - L
    return INDENT + "─"*L + col + "─"*R

def _fmt_metric(v: Any, unit: str) -> str:
    try: x=float(v)
    except: return "—"
    u=(unit or "").lower()
    if u in {"$","usd","usdt","usdc"}:
        if abs(x)>=1e6: return f"${x/1e6:.1f}m".replace(".0m","m")
        if abs(x)>=1e3: return f"${x/1e3:.1f}k".replace(".0k","k")
        return f"${x:,.2f}"
    if u in {"%","pct","percent"}: return f"{x:.2f}%"
    if u in {"bp","bps"}: return f"{x:.0f}bp"
    return f"{x:.4g}"

def _fmt_threshold(meta: Dict[str,Any]) -> str:
    thr = (meta or {}).get("threshold") or {}
    op  = (thr.get("op") or thr.get("operator") or "").strip()
    val = thr.get("value"); unit = thr.get("unit") or ""
    if val is None: return "—"
    sym = {"<":"＜","<=":"≤",">":"＞",">=":"≥","==":"＝"}.get(op, "")
    txt = _fmt_metric(val, unit)
    return f"{sym} {txt}".strip() if sym else txt

def _fmt_state(s: str) -> str:
    st=(s or "OK").upper()
    return f"{STATE_ICON.get(st,'·')} {st}"

def _fmt_age(ts: Any) -> str:
    if not ts: return "—"
    try:
        if isinstance(ts,(int,float)): dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
        else: dt = datetime.fromisoformat(str(ts).replace("Z","+00:00"))
        d = (datetime.now(timezone.utc) - dt).total_seconds()
        if d < 0: d = 0
        return f"{int(d)}s" if d < 90 else (f"{int(d//60)}m" if d < 5400 else f"{int(d//3600)}h")
    except: return "—"

# ===== data access =====
def _get_latest_cycle(cur) -> Optional[str]:
    for t in ("monitor_status","monitor_statuses","monitor_status_log"):
        try:
            cur.execute(f"SELECT MAX(cycle_id) FROM {t}")
            r=cur.fetchone()
            if r and r[0]: return r[0]
        except: continue
    try:
        cur.execute("SELECT MAX(cycle_id) FROM sonic_monitor_ledger")
        r=cur.fetchone()
        if r and r[0]: return r[0]
    except: pass
    return None

def _load_monitor_status(cur, table: str, cid: str) -> List[Dict[str,Any]]:
    try:
        cur.execute(f"PRAGMA table_info({table})")
        cols=[r[1] for r in cur.fetchall()]
        mon = next((c for c in cols if c in ("monitor","group","kind","category")), "monitor")
        lab = next((c for c in cols if c in ("label","name","title")), "label")
        st  = next((c for c in cols if c in ("state","status")), "state")
        val = next((c for c in cols if c in ("value","val","metric","metric_value")), "value")
        uni = next((c for c in cols if c in ("unit","u","metric_unit")), "unit")
        meta= next((c for c in cols if c in ("meta","payload","extra","details")), "meta")
        ts  = next((c for c in cols if c in ("ts","timestamp","updated_at","time","at")), "ts")
        cur.execute(f"SELECT {mon},{lab},{st},{val},{uni},{meta},{ts} FROM {table} WHERE cycle_id=?", (cid,))
        out=[]
        for row in cur.fetchall():
            md = row[5]
            if isinstance(md,str):
                try: md=json.loads(md)
                except: md={}
            out.append({
                "monitor": (row[0] or "custom"),
                "label":   row[1] or "",
                "state":   (row[2] or "OK"),
                "value":   row[3],
                "unit":    row[4] or (md.get("unit") if isinstance(md,dict) else ""),
                "meta":    md if isinstance(md,dict) else {},
                "ts":      row[6],
                "source":  (md or {}).get("source") or (row[0] or "")[:6],
            })
        return out
    except: return []

def _load_from_ledger(cur, cid: str) -> List[Dict[str,Any]]:
    try:
        cur.execute("PRAGMA table_info(sonic_monitor_ledger)")
        cols=[r[1] for r in cur.fetchall()]
        if "payload" not in cols: return []
        cur.execute("SELECT name,payload FROM sonic_monitor_ledger WHERE cycle_id=?", (cid,))
        out=[]
        for mon, payload in cur.fetchall():
            try: p=json.loads(payload)
            except: continue
            sts = p.get("statuses")
            if isinstance(sts, list) and sts:
                for it in sts:
                    if not isinstance(it, dict): continue
                    thr = it.get("threshold") or {}
                    out.append({
                        "monitor": (mon or "custom"),
                        "label": it.get("label") or it.get("name") or mon,
                        "state": (it.get("state") or it.get("status") or "OK"),
                        "value": it.get("value"),
                        "unit":  it.get("unit",""),
                        "meta":  {"threshold": thr, "source": p.get("source"), "ts": p.get("ts")},
                        "ts":    p.get("ts"),
                        "source": p.get("source") or (mon or "")[:6],
                    })
            else:
                out.append({
                    "monitor": (mon or "custom"),
                    "label":   (p.get("result") or p.get("source") or mon),
                    "state":   (p.get("state") or "OK"),
                    "value":   p.get("value"),
                    "unit":    p.get("unit",""),
                    "meta":    p,
                    "ts":      p.get("ts"),
                    "source":  p.get("source") or (mon or "")[:6],
                })
        return out
    except: return []

def _latest_rows(dl: Any) -> Tuple[List[Dict[str,Any]], str]:
    # Prefer dl.monitors if present
    try:
        mm = getattr(dl, "monitors", None)
        if mm is not None:
            rs = mm.latest()
            if rs:
                return rs, "dl.monitors"
    except Exception:
        pass
    try:
        cur = dl.db.get_cursor()
    except: return [], "db.monitor_status"
    cid = _get_latest_cycle(cur)
    if not cid: return [], "db.monitor_status"
    for t in ("monitor_status","monitor_statuses","monitor_status_log"):
        rs=_load_monitor_status(cur,t,cid)
        if rs: return rs,t
    rs=_load_from_ledger(cur,cid)
    return (rs,"sonic_monitor_ledger") if rs else ([], "db.monitor_status")

# ===== normalize/sort =====
def _norm(r: Dict[str,Any]) -> Dict[str,Any]:
    m=(r.get("monitor") or "custom").lower()
    s=(r.get("state") or "OK").upper()
    return {
        "monitor": m,
        "label":   r.get("label") or "",
        "state":   s,
        "value":   r.get("value"),
        "unit":    r.get("unit") or "",
        "meta":    r.get("meta") or {},
        "ts":      r.get("ts"),
        "source":  (r.get("source") or m)[:W_SRC],
    }

def _sort_key(r: Dict[str,Any]) -> Tuple[int,int,str]:
    return (SEVERITY_RANK.get(r["state"],4), MON_RANK.get(r["monitor"],9), r["label"])

# ===== render =====
def render(dl, *_args, **_kw) -> None:
    raw, src = _latest_rows(dl)
    rows=[_norm(r) for r in raw]
    rows.sort(key=_sort_key)

    print()
    print(_hr("Monitors"))
    header = (
        INDENT
        + _pad(HEADER_IC["mon"]+"Mon", W_MON)
        + SEP + _pad(HEADER_IC["thr"]+"Thresh", W_TH)
        + SEP + _pad(HEADER_IC["val"]+"Value",  W_VAL, right=True)
        + SEP + _pad(HEADER_IC["st"] +"State",  W_ST)
        + SEP + _pad(HEADER_IC["age"]+"Age",    W_AGE, right=True)
        + SEP + _pad(HEADER_IC["src"]+"Src",    W_SRC)
    )
    print(header)
    print(INDENT + "─"*HR_WIDTH)

    if not rows:
        print(f"{INDENT}[MON] source: {src} (0 rows)")
        print(f"{INDENT}(no monitor results)")
        print()
        return

    for r in rows:
        icon = MON_ICON.get(r["monitor"], "🧪")
        mon  = f"{icon} {r['label'] or r['monitor'].title()}"
        thr  = _fmt_threshold(r["meta"])
        val  = _fmt_metric(r["value"], r["unit"])
        stxt = _fmt_state(r["state"])
        tsx  = r.get("meta",{}).get("ts") or r.get("ts")
        age  = _fmt_age(tsx)
        print(
            INDENT
            + _pad(mon, W_MON)
            + SEP + _pad(thr, W_TH)
            + SEP + _pad(val, W_VAL, right=True)
            + SEP + _pad(stxt, W_ST)
            + SEP + _pad(age, W_AGE, right=True)
            + SEP + _pad(r["source"], W_SRC)
        )

    n_ok   = sum(1 for x in rows if x["state"]=="OK")
    n_warn = sum(1 for x in rows if x["state"]=="WARN")
    n_snz  = sum(1 for x in rows if x["state"]=="SNOOZE")
    n_br   = sum(1 for x in rows if x["state"]=="BREACH")
    ages   = []
    for x in rows:
        t = x.get("meta",{}).get("ts") or x.get("ts")
        ages.append(_fmt_age(t))
    last_age = ages[0] if ages else "—"
    print(INDENT + f"Summary:  {STATE_ICON['OK']} {n_ok}   {STATE_ICON['WARN']} {n_warn}   {STATE_ICON['SNOOZE']} {n_snz}   {STATE_ICON['BREACH']} {n_br}    last update {last_age}")
    print()
