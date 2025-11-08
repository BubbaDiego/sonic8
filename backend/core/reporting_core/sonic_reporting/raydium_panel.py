from __future__ import annotations

"""
raydium_panel.py
Sonic Reporting — Raydium LPs panel (console)

Style: same as other Sonic panels
- centered title rail
- solid rule above the column headers
- tidy columns, total row, checked-at stamp

This module is forgiving about call shapes:
  render(ctx)
  render(ctx, width)
  render(dl, ctx)
  render(ctx, **kwargs)
  connector(...) is an alias to render(...).
"""

import os
import datetime as _dt
from typing import Any, Dict, Iterable, List, Optional, Tuple

PANEL_KEY = "raydium_panel"
PANEL_NAME = "Raydium LPs"


# ────────────────────────────────────────────────────────────────────────────────
# Console helpers
# ────────────────────────────────────────────────────────────────────────────────

def _console_width(default: int = 92) -> int:
    try:
        w = int(os.environ.get("SONIC_CONSOLE_WIDTH", default))
        return max(60, min(180, w))
    except Exception:
        return default


def _hr(width: Optional[int] = None, ch: str = "─") -> str:
    W = width or _console_width()
    return ch * W


def _title_rail(title: str, width: Optional[int] = None, ch: str = "─") -> str:
    W = width or _console_width()
    t = f"  {title.strip()}  "
    fill = max(0, W - len(t))
    left = fill // 2
    right = fill - left
    return f"{ch * left}{t}{ch * right}"


def _abbr_middle(s: str, front: int = 4, back: int = 4, min_len: int = 12) -> str:
    s = ("" if s is None else str(s)).strip()
    if len(s) <= min_len or len(s) <= front + back + 3:
        return s
    return f"{s[:front]}…{s[-back:]}"


def _fmt_usd(v: Any) -> str:
    try:
        x = float(v)
        return f"${int(round(x)):,}" if abs(x - round(x)) < 1e-6 else f"${x:,.2f}"
    except Exception:
        return "—"


def _fmt_lp(v: Any) -> str:
    if v in (None, "", 0, 0.0):
        return "—"
    try:
        x = float(v)
        if x == 0:
            return "—"
        if abs(x) < 0.001:
            return f"{x:.4f}"
        if abs(x) < 1:
            return f"{x:.3f}"
        return f"{x:.2f}"
    except Exception:
        return str(v)


def _fmt_apr(v: Any) -> str:
    try:
        x = float(v)
        return f"{x:.1f}%"
    except Exception:
        return "—"


def _fmt_time(ts: Any) -> str:
    if ts is None:
        dt = _dt.datetime.now()
    elif isinstance(ts, (int, float)):
        dt = _dt.datetime.fromtimestamp(float(ts))
    elif isinstance(ts, _dt.datetime):
        dt = ts
    else:
        s = str(ts).strip()
        try:
            if s.endswith("Z"):
                dt = _dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
            else:
                dt = _dt.datetime.fromisoformat(s)
        except Exception:
            dt = _dt.datetime.now()
    hour = dt.strftime("%I").lstrip("0") or "0"
    return f"{hour}:{dt.strftime('%M%p').lower()}"


# ────────────────────────────────────────────────────────────────────────────────
# Data normalization
# ────────────────────────────────────────────────────────────────────────────────

def _norm_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    if rec is None:
        rec = {}

    pool = rec.get("pool") or rec.get("pool_name") or rec.get("amm") or rec.get("pair") or rec.get("symbol") or rec.get("collection") or ""
    address = rec.get("address") or rec.get("owner") or rec.get("pubkey") or rec.get("mint") or ""
    lp_qty = rec.get("lp_qty") or rec.get("qty") or rec.get("balance") or rec.get("amount") or rec.get("raw_amount")
    usd_value = rec.get("usd_value") or rec.get("usd") or rec.get("value_usd") or rec.get("fiat_value") or 0.0
    apr = rec.get("apr") or rec.get("apy") or rec.get("est_apr")
    checked_ts = rec.get("checked_ts") or rec.get("ts") or rec.get("timestamp")

    return {
        "pool": str(pool) if pool is not None else "",
        "address": str(address) if address is not None else "",
        "lp_qty": lp_qty,
        "usd_value": usd_value,
        "apr": apr,
        "checked_ts": checked_ts,
    }


def _coalesce(*vals, default=None):
    for v in vals:
        if v not in (None, ""):
            return v
    return default


def _collect_records(ctx: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    # 1) direct on context
    direct = ctx.get("records")
    if isinstance(direct, list) and direct:
        return [_norm_record(r or {}) for r in direct], "ctx.records"

    rayd = ctx.get("raydium")
    if isinstance(rayd, list) and rayd:
        return [_norm_record(r or {}) for r in rayd], "ctx.raydium"
    if isinstance(rayd, dict):
        seq = rayd.get("records") or rayd.get("positions") or rayd.get("lps") or []
        if isinstance(seq, list) and seq:
            return [_norm_record(r or {}) for r in seq], "ctx.raydium.records"

    # 2) from summary
    csum = ctx.get("csum") or ctx.get("summary") or {}
    seq = _coalesce((csum.get("raydium") or {}).get("records"),
                    (csum.get("raydium") or {}).get("lps"),
                    default=None)
    if isinstance(seq, list) and seq:
        return [_norm_record(r or {}) for r in seq], "csum.raydium"

    # 3) DataLocker provider
    dl = ctx.get("dl")
    provider = getattr(dl, "raydium", None)
    if provider:
        for name in ("get_latest_lp_positions", "get_lp_positions", "get_positions", "list_lp_nfts", "list_positions"):
            fn = getattr(provider, name, None)
            if callable(fn):
                try:
                    res = fn()
                    arr = (res.get("records") if isinstance(res, dict) else res) or []
                    if isinstance(arr, list) and arr:
                        return [_norm_record(r or {}) for r in arr], f"dl.raydium.{name}()"
                except Exception:
                    pass
        # attributes
        for attr in ("records", "positions", "lps", "items"):
            arr = getattr(provider, attr, None)
            if isinstance(arr, list) and arr:
                return [_norm_record(r or {}) for r in arr], f"dl.raydium.{attr}"

    return [], "none"


# ────────────────────────────────────────────────────────────────────────────────
# Rendering (positional-args tolerant)
# ────────────────────────────────────────────────────────────────────────────────

def render(context: Optional[Dict[str, Any]] = None, *args, **kwargs) -> List[str]:
    """
    Accepted shapes:
      render(ctx)
      render(ctx, width)
      render(dl, ctx)
      render(ctx, csum={...})
      render(..., width=92)
    """
    ctx: Dict[str, Any] = {}
    if context:
        ctx.update(context)

    # absorb extra positionals commonly sent by the sequencer
    if len(args) >= 1:
        a0 = args[0]
        if isinstance(a0, dict):
            ctx.update(a0)
        else:
            # DataLocker instance or other helper
            ctx.setdefault("dl", a0)
    if len(args) >= 2:
        a1 = args[1]
        if isinstance(a1, dict):
            ctx.update(a1)
        elif isinstance(a1, (int, float)):
            kwargs.setdefault("width", int(a1))

    if kwargs:
        ctx.update(kwargs)

    width = ctx.get("width") or _console_width()

    out: List[str] = []
    out.append(_title_rail("Raydium LPs", width))
    out.append(_hr(width))  # solid rule above headers

    # Column spec (kept in sync with other panels)
    col_pool = 22
    col_addr = 34
    col_lp = 9
    col_usd = 12
    col_apr = 7
    col_chk = 10

    def fmt_row(pool, addr, lp, usd, apr, chk) -> str:
        pool = _abbr_middle(pool or "", 6, 6, min_len=col_pool)
        addr = _abbr_middle(addr or "", 6, 6, min_len=col_addr)
        lp = (lp or "").rjust(col_lp)
        usd = (usd or "").rjust(col_usd)
        apr = (apr or "").rjust(col_apr)
        chk = (chk or "").rjust(col_chk)
        line = (
            f"{pool:<{col_pool}}  "
            f"{addr:<{col_addr}}  "
            f"{lp}{' ' * 2}{usd}{' ' * 2}{apr}{' ' * 2}{chk}"
        )
        return line[:width] if len(line) > width else line

    out.append(fmt_row("Pool", "Address", "LP", "USD", "APR", "Checked"))

    records, source = _collect_records(ctx)

    total_usd = 0.0
    last_ts = None

    if records:
        for rec in records:
            total_usd += float(rec.get("usd_value") or 0.0)
            ts = rec.get("checked_ts")
            if ts:
                last_ts = ts
            out.append(fmt_row(
                rec.get("pool", ""),
                rec.get("address", ""),
                _fmt_lp(rec.get("lp_qty")),
                _fmt_usd(rec.get("usd_value")),
                _fmt_apr(rec.get("apr")),
                _fmt_time(ts) if ts else "",
            ))
    else:
        out.append("(no raydium positions)")

    out.append("")
    out.append(f"  Total (USD): {_fmt_usd(total_usd)}")
    out.append(f"  Checked: {_fmt_time(last_ts) if last_ts else _fmt_time(None)}")
    out.append(f"[RAY] source={source} count={len(records)}")
    return out


def connector(*args, **kwargs) -> List[str]:
    """Sequencer-friendly entrypoint; simply delegates to render."""
    return render(*args, **kwargs)


def name() -> str:
    return PANEL_NAME


if __name__ == "__main__":
    demo = [{
        "pool": "So1111…/EPjF…",
        "address": "2jn9ve…dSU9pj",
        "lp_qty": 1.23456,
        "usd_value": 106,
        "apr": None,
        "checked_ts": _dt.datetime.now().isoformat(timespec="seconds"),
    }]
    for ln in render({"records": demo}):
        print(ln)
