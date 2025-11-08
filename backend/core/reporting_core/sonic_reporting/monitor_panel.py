# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
import json, os, unicodedata

# ===== colors (title/header text only) =====
USE_COLOR   = os.getenv("SONIC_COLOR", "1").strip().lower() not in {"0","false","no","off"}
TITLE_COLOR = os.getenv("SONIC_TITLE_COLOR", "\x1b[38;5;45m")  # cyan/teal
HEAD_COLOR  = os.getenv("SONIC_HEAD_COLOR",  "\x1b[38;5;81m")  # bright teal
def _c(s: str, color: str) -> str: return f"{color}{s}\x1b[0m" if USE_COLOR else s

# ===== layout =====
HR_WIDTH = 78
INDENT   = "  "
# icon + 5 columns (tight)
W_ICON, W_MON, W_TH, W_VAL, W_ST, W_AGE, W_SRC = 3, 21, 10, 10, 8, 6, 8
SEP = " "

# icons & ordering
STATE_ICON   = {"OK":"✅","WARN":"⚠︎","BREACH":"🔥","SNOOZE":"🔕"}
MON_ICON     = {"liquid":"💧","profit":"💹","market":"📈","custom":"🧪","prices":"💵","positions":"📊","raydium":"🪙","hedges":"🪶","reporters":"🧭","heartbeat":"💓"}
SEVERITY_RANK= {"BREACH":0,"SNOOZE":1,"WARN":2,"OK":3}
MON_RANK     = {"liquid":0,"profit":1,"market":2,"custom":3,"prices":4,"positions":5,"raydium":6,"hedges":7,"reporters":8,"heartbeat":9}

# ===== emoji-safe padding =====
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
    if L>=w:
        while t and _dl(t)>w: t=t[:-1]
        return t
    pad = " "*(w-L)
    return (pad+t) if right else (t+pad)
def _pad_center(s: Any, w: int) -> str:
    t = "" if s is None else str(s)
    L = _dl(t)
    if L>=w:
        while t and _dl(t)>w: t=t[:-1]
        return t
    total=w-L; left=total//2; right=total-left
    return (" "*left)+t+(" "*right)

# ===== visuals =====
def _hr(title: str) -> str:
    plain = f"  {title} "
    col   = f" {_c('🔎  ' + title, TITLE_COLOR)} "
    pad = HR_WIDTH - len(plain)
    if pad < 0: pad = 0
    L=pad//2; R=pad-L
    return INDENT + "─"*L + col + "─"*R

# ===== metric formatters (no % symbols) =====
def _fmt_metric(v: Any, unit: str) -> str:
    try: x=float(v)
    except: return "—"
    u=(unit or "").lower()
    if u in {"$","usd","usdt","usdc"}:
        if abs(x)>=1e6: return f"{x/1e6:.1f}m".replace(".0m","m")
        if abs(x)>=1e3: return f"{x/1e3:.1f}k".replace(".0k","k")
        return f"{x:,.2f}"
    # percent or other: show number only (no '%' suffix)
    if abs(x)>=1000: return f"{x:,.0f}"
    if abs(x)>=1:    return f"{x:.2f}"
    return f"{x:.3f}"

def _fmt_threshold_row(row: Dict[str,Any]) -> str:
    """
    Resolve threshold from row columns thr_op/thr_value/thr_unit first,
    else fallback to meta.threshold. No '%' symbol in output.
    """
    op = (row.get("thr_op") or "").strip()
    tv = row.get("thr_value")
    tu = row.get("thr_unit") or ""
    if op and tv is not None:
        sym={"<":"＜","<=":"≤",">":"＞",">=":"≥","==":"＝"}.get(op,"")
        txt=_fmt_metric(tv, tu)
        return f"{sym} {txt}".strip() if sym else txt

    meta = row.get("meta") or {}
    if isinstance(meta, str):
        try: meta=json.loads(meta)
        except: meta={}
    thr=(meta or {}).get("threshold") or {}
    op  =(thr.get("op") or thr.get("operator") or "").strip()
    val = thr.get("value"); unit = thr.get("unit") or ""
    if val is None: return "—"
    sym={"<":"＜","<=":"≤",">":"＞",">=":"≥","==":"＝"}.get(op,"")
    txt=_fmt_metric(val, unit)
    return f"{sym} {txt}".strip() if sym else txt

def _fmt_state(s: str) -> str:
    st=(s or "OK").upper()
    return f"{STATE_ICON.get(st,'·')} {st}"

def _fmt_age(ts: Any) -> str:
    if not ts: return "—"
    try:
        if isinstance(ts,(int,float)):
            dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(ts).replace("Z","+00:00"))
        d=(datetime.now(timezone.utc)-dt).total_seconds()
        if d<0: d=0
        return f"{int(d)}s" if d<90 else (f"{int(d//60)}m" if d<5400 else f"{int(d//3600)}h")
    except: return "—"

# ===== manager-first; tolerant fallbacks =====
def _latest_rows_via_manager(dl: Any) -> Optional[List[Dict[str,Any]]]:
    try:
        mm=getattr(dl,"monitors",None)
        if mm is not None:
            rs=mm.latest()
            if rs: return rs
    except: pass
    return None

def _get_latest_cycle(cur) -> Optional[str]:
    for t in ("monitor_status","monitor_statuses","monitor_status_log"):
        try:
            cur.execute(f"SELECT MAX(cycle_id) FROM {t}")
            r=cur.fetchone()
            if r and r[0]: return r[0]
        except: continue
    try:
        cur.execute("SELECT MAX(cycle_id) FROM monitor_ledger")
        r=cur.fetchone()
        if r and r[0]: return r[0]
    except: pass
    return None

def _load_status_table(cur, table: str, cid: str) -> List[Dict[str,Any]]:
    try:
        cur.execute(f"PRAGMA table_info({table})")
        cols=[r[1] for r in cur.fetchall()]
        mon=next((c for c in cols if c in ("monitor","group","kind","category")), "monitor")
        lab=next((c for c in cols if c in ("label","name","title")), "label")
        st =next((c for c in cols if c in ("state","status")), "state")
        val=next((c for c in cols if c in ("value","val","metric","metric_value")), "value")
        uni=next((c for c in cols if c in ("unit","u","metric_unit")), "unit")
        thr_op= "thr_op" if "thr_op" in cols else None
        thr_val= "thr_value" if "thr_value" in cols else None
        thr_unit= "thr_unit" if "thr_unit" in cols else None
        meta=next((c for c in cols if c in ("meta","payload","extra","details","metadata")), "meta")
        ts =next((c for c in cols if c in ("ts","timestamp","updated_at","time","at")), "ts")

        # build select list dynamically to keep mapping simple
        sel = [mon, lab, st, val, uni, meta, ts]
        if thr_op:  sel.append(thr_op)
        if thr_val: sel.append(thr_val)
        if thr_unit:sel.append(thr_unit)

        cur.execute(f"SELECT {', '.join(sel)} FROM {table} WHERE cycle_id=?", (cid,))
        out=[]
        for row in cur.fetchall():
            base = {
                "monitor": row[0] or "custom",
                "label":   row[1] or "",
                "state":   (row[2] or "OK"),
                "value":   row[3],
                "unit":    row[4] or "",
                "meta":    {},
                "ts":      row[6] if len(row)>=7 else None,
                "source":  "",  # set later
                "thr_op":  None, "thr_value": None, "thr_unit": None,
            }
            md = row[5]
            if isinstance(md,str):
                try: md=json.loads(md)
                except: md={}
            if isinstance(md,dict):
                base["meta"]=md
                base["unit"]= base["unit"] or md.get("unit","")
                base["source"]= md.get("source") or base["monitor"]
                if base["ts"] is None:
                    base["ts"]= md.get("ts")
            # threshold columns if present
            idx = 7
            if thr_op:   base["thr_op"]   = row[idx]; idx+=1
            if thr_val:  base["thr_value"]= row[idx]; idx+=1
            if thr_unit: base["thr_unit"] = row[idx]; idx+=1
            # fallback source
            base["source"]= base["source"] or base["monitor"]
            out.append(base)
        return out
    except: return []

def _load_from_ledger(cur, cid: str) -> List[Dict[str,Any]]:
    try:
        cur.execute("PRAGMA table_info(monitor_ledger)")
        cols=[r[1] for r in cur.fetchall()]
        if "payload" not in cols: return []
        cur.execute("SELECT monitor_name, payload FROM monitor_ledger WHERE cycle_id=?", (cid,))
        out=[]
        for mon, payload in cur.fetchall():
            try: p=json.loads(payload)
            except: continue
            sts=p.get("statuses")
            if isinstance(sts,list) and sts:
                for it in sts:
                    if not isinstance(it,dict): continue
                    thr=it.get("threshold") or {}
                    out.append({
                        "monitor": (mon or "custom"),
                        "label":   it.get("label") or it.get("name") or mon,
                        "state":   (it.get("state") or it.get("status") or "OK"),
                        "value":   it.get("value"),
                        "unit":    it.get("unit",""),
                        "meta":    {"threshold": thr, "source": p.get("source"), "ts": p.get("ts")},
                        "ts":      p.get("ts"),
                        "source":  p.get("source") or (mon or ""),
                        "thr_op":  None, "thr_value": None, "thr_unit": None,
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
                    "source":  p.get("source") or (mon or ""),
                    "thr_op":  None, "thr_value": None, "thr_unit": None,
                })
        return out
    except: return []

def _latest_rows(dl: Any) -> Tuple[List[Dict[str,Any]], str]:
    rs=_latest_rows_via_manager(dl)
    if rs: return rs, "dl.monitors"
    try:
        cur=dl.db.get_cursor()
        cid=_get_latest_cycle(cur)
        if not cid: return [], "monitor_status"
        for t in ("monitor_status","monitor_statuses","monitor_status_log"):
            rows=_load_status_table(cur,t,cid)
            if rows: return rows, t
        rows=_load_from_ledger(cur,cid)
        if rows: return rows, "monitor_ledger"
    except: pass
    return [], "monitor_status"

def _norm(r: Dict[str,Any]) -> Dict[str,Any]:
    m=(r.get("monitor") or "custom").lower()
    s=(r.get("state") or "OK").upper()
    meta=r.get("meta") or {}
    ts=meta.get("ts") or r.get("ts")
    return {
        "monitor": m,
        "label":   r.get("label") or "",
        "state":   s,
        "value":   r.get("value"),
        "unit":    r.get("unit") or "",
        "meta":    meta if isinstance(meta,dict) else {},
        "ts":      ts,
        "source":  r.get("source") or m,
        "thr_op":  r.get("thr_op"),
        "thr_value": r.get("thr_value"),
        "thr_unit":  r.get("thr_unit"),
    }

def _sort_key(r: Dict[str,Any]) -> Tuple[int,int,str]:
    return (SEVERITY_RANK.get(r["state"],4), MON_RANK.get(r["monitor"],9), r["label"])

# ===== render =====
def render(dl, *_args, **_kw) -> None:
    raw, _ = _latest_rows(dl)
    rows=[_norm(r) for r in raw]
    rows.sort(key=_sort_key)

    print()
    print(_hr("Monitors"))

    # header (colored text only)
    h_mon  = _c("Mon",    HEAD_COLOR)
    h_thr  = _c("Thresh", HEAD_COLOR)
    h_val  = _c("Value",  HEAD_COLOR)
    h_st   = _c("State",  HEAD_COLOR)
    h_age  = _c("Age",    HEAD_COLOR)
    h_src  = _c("Source", HEAD_COLOR)

    print(
        INDENT
        + _pad("", W_ICON)
        + _pad(h_mon, W_MON)
        + SEP + _pad(h_thr, W_TH)
        + SEP + _pad(h_val, W_VAL, right=True)
        + SEP + _pad_center(h_st, W_ST)
        + SEP + _pad(h_age, W_AGE, right=True)
        + SEP + _pad(h_src, W_SRC)
    )
    print(INDENT + "─"*HR_WIDTH)

    if not rows:
        print(f"{INDENT}(no monitor results)")
        print()
        return

    for r in rows:
        icon = MON_ICON.get(r["monitor"], "🧪") + " "
        mon  = r["label"] or r["monitor"].title()
        # threshold: from columns thr_* first, then meta.threshold (no '%' printed)
        thr  = _fmt_threshold_row(r)
        val  = _fmt_metric(r["value"], r["unit"])
        stxt = f"{STATE_ICON.get(r['state'],'·')} {r['state']}"
        age  = _fmt_age(r["ts"])
        src  = r["source"]

        print(
            INDENT
            + _pad(icon, W_ICON)
            + _pad(mon, W_MON)
            + SEP + _pad(thr, W_TH)
            + SEP + _pad(val, W_VAL, right=True)
            + SEP + _pad_center(stxt, W_ST)
            + SEP + _pad(age, W_AGE, right=True)
            + SEP + _pad(src, W_SRC)
        )

    # summary
    n_ok   = sum(1 for x in rows if x["state"]=="OK")
    n_warn = sum(1 for x in rows if x["state"]=="WARN")
    n_snz  = sum(1 for x in rows if x["state"]=="SNOOZE")
    n_br   = sum(1 for x in rows if x["state"]=="BREACH")
    ages   = [_fmt_age(x.get("ts")) for x in rows if x.get("ts")]
    last_age = ages[0] if ages else "—"
    print(INDENT + f"Summary:  {STATE_ICON['OK']} {n_ok}  {STATE_ICON['WARN']} {n_warn}  {STATE_ICON['SNOOZE']} {n_snz}  {STATE_ICON['BREACH']} {n_br}   last update {last_age}")
    print()
