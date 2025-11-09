# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
import unicodedata
import os

# standardized title via console_panels.theming
from .console_panels.theming import (
    console_width as _theme_width,
    hr as _theme_hr,
    title_lines as _theme_title,
)
PANEL_SLUG = "wallets"
PANEL_NAME = "Wallets"

# ===== colors (only text is colored; rules stay plain) =====
USE_COLOR     = os.getenv("SONIC_COLOR", "1").strip().lower() not in {"0","false","no","off"}
TITLE_COLOR   = os.getenv("SONIC_TITLE_COLOR", "\x1b[38;5;45m")
TOTALS_COLOR  = os.getenv("SONIC_TOTALS_COLOR", "\x1b[38;5;214m")
def _c(s: str, color: str) -> str:
    return f"{color}{s}\x1b[0m" if USE_COLOR else s

# ===== layout =====
HR_WIDTH = 78
INDENT   = "  "
W_NAME, W_CHAIN, W_ADDR, W_BAL, W_USD, W_CHK = 12, 7, 24, 8, 9, 8
SEP = "  "
HEADER_IC = {"name":"👤","chain":"⛓","addr":"🔑","bal":"🪙","usd":"💵","chk":"⏱"}

# ===== emoji-safe padding =====
_VAR = {0xFE0F, 0xFE0E}
_ZW  = {0x200D, 0x200C}
def _disp_len(s: str) -> int:
    total = 0
    for ch in s:
        cp = ord(ch)
        if cp in _VAR or cp in _ZW: continue
        ew = unicodedata.east_asian_width(ch)
        total += 2 if ew in ("W","F") else 1
    return total

def _padw(text: Any, w: int, *, right=False) -> str:
    s = "" if text is None else str(text)
    cur = _disp_len(s)
    if cur >= w:
        while s and _disp_len(s) > w: s = s[:-1]
        return s
    pad = " " * (w - cur)
    return (pad + s) if right else (s + pad)

def _pad(s: Any, w: int, right: bool=False) -> str:
    return _padw(s, w, right=right)

# ===== visuals =====
def _abbr_addr(a: Any) -> str:
    s = "" if a is None else str(a)
    return "—" if not s else (s if len(s) <= 12 else f"{s[:6]}…{s[-4:]}")

def _fmt_usd(x: Any, w: int, *, right=True) -> str:
    try: v = float(x)
    except: return _pad("—", w, right=right)
    if abs(v) >= 1e6: s = f"${v/1e6:.1f}m".replace(".0m","m")
    elif abs(v) >= 1e3: s = f"${v/1e3:.1f}k".replace(".0k","k")
    else: s = f"${v:,.2f}"
    return _pad(s, w, right=right)

def _fmt_bal(x: Any, w: int, *, right=True) -> str:
    try: v = float(x)
    except: return _pad("—", w, right=right)
    if abs(v) >= 1e3: s = f"{int(round(v))}"
    elif abs(v) >= 1: s = f"{v:.2f}"
    elif abs(v) >= .01: s = f"{v:.3f}"
    else: s = f"{v:.4f}"
    return _pad(s, w, right=right)

def _fmt_age(val: Any, w: int) -> str:
    try:
        if isinstance(val,(int,float)):
            delta = float(val)
        else:
            t = str(val)
            if t.endswith("Z"):
                dt = datetime.fromisoformat(t.replace("Z","+00:00"))
            else:
                dt = datetime.fromisoformat(t)
            delta = (datetime.now(dt.tzinfo or None) - dt).total_seconds()
        if delta < 90: s = f"{int(delta)}s"
        elif delta < 5400: s = f"{int(delta//60)}m"
        else: s = f"{int(delta//3600)}h"
        return _pad(s, w, right=True)
    except:
        return _pad("—", w, right=True)

# ===== data =====
def _get_wallets(dl: Any) -> List[Dict[str,Any]]:
    mgr = getattr(dl, "wallets", None)
    if mgr and hasattr(mgr, "get_wallets"):
        try:
            rows = mgr.get_wallets() or []
            return [r if isinstance(r,dict) else (getattr(r,"dict",lambda:{})() or getattr(r,"__dict__",{}) or {}) for r in rows]
        except Exception as e:
            print(f"[REPORT] wallets_panel: dl.wallets.get_wallets failed: {e}")
    fn = getattr(dl, "read_wallets", None)
    if callable(fn):
        try:
            return fn() or []
        except Exception as e:
            print(f"[REPORT] wallets_panel: dl.read_wallets failed: {e}")
    return []

# ===== render =====
def render(dl, *_args, **_kw) -> None:
    rows = _get_wallets(dl)

    width = _theme_width()
    print()
    print(_theme_hr(width))
    for ln in _theme_title(PANEL_SLUG, PANEL_NAME, width=width):
        print(ln)
    print(_theme_hr(width))
    header = (
        INDENT
        + _pad(HEADER_IC["name"] + "Name",  W_NAME)
        + SEP + _pad(HEADER_IC["chain"] + "Chain", W_CHAIN)
        + SEP + _pad(HEADER_IC["addr"] + "Address", W_ADDR)
        + SEP + _pad(HEADER_IC["bal"]  + "Balance", W_BAL)
        + SEP + _pad(HEADER_IC["usd"]  + "USD",     W_USD)
        + SEP + _pad(HEADER_IC["chk"]  + "Checked", W_CHK)
    )
    print(header)
    print(INDENT + "─"*HR_WIDTH)

    if not rows:
        print(f"{INDENT}[WALLETS] source: dl.wallets.get_wallets (0 rows)")
        print(f"{INDENT}(no wallets)")
        print()
        return

    norm: List[Dict[str,Any]] = []
    for r in rows:
        d = r if isinstance(r,dict) else (getattr(r,"dict",lambda:{})() or getattr(r,"__dict__",{}) or {})
        norm.append({
            "name":  d.get("name") or d.get("label") or "—",
            "chain": d.get("chain") or d.get("network") or d.get("type") or "—",
            "addr":  d.get("public_address") or d.get("address") or d.get("pubkey") or d.get("pub_key") or "",
            "bal":   d.get("balance") or d.get("native") or d.get("sol") or d.get("amount"),
            "usd":   d.get("usd") or d.get("balance_usd") or d.get("fiat_usd"),
            "chk":   d.get("checked_at") or d.get("updated_at") or d.get("ts"),
            "active": bool(d.get("is_active")),
        })

    total_bal = 0.0
    total_usd = 0.0
    for n in norm:
        try: total_bal += float(n["bal"] or 0.0)
        except: pass
        try: total_usd += float(n["usd"] or 0.0)
        except: pass

    for n in norm:
        star = "★ " if n["active"] else "  "
        print(
            INDENT
            + _pad(star + n["name"], W_NAME)
            + SEP + _pad(n["chain"], W_CHAIN)
            + SEP + _pad(_abbr_addr(n["addr"]), W_ADDR)
            + SEP + _fmt_bal(n["bal"], W_BAL, right=True)
            + SEP + _fmt_usd(n["usd"], W_USD, right=True)
            + SEP + _fmt_age(n["chk"], W_CHK)
        )

    totals = (
        INDENT
        + _pad("", W_NAME) + SEP + _pad("Totals", W_CHAIN)
        + SEP + _pad("—", W_ADDR)
        + SEP + _fmt_bal(total_bal, W_BAL, right=False)
        + SEP + _fmt_usd(total_usd, W_USD, right=False)
        + SEP + _pad("", W_CHK)
    )
    print(_c(totals, TOTALS_COLOR))
    print()
