from __future__ import annotations

"""
raydium_panel.py
Sonic Reporting — Raydium LPs panel (console)

Goals:
- Match the same console style as other Sonic panels (title rail, header rule, aligned columns).
- Be forgiving about inputs: accept records from context/summary or query dl.raydium if present.
- Always print a total USD line and a "Checked:" stamp at the bottom.
"""

import os
import math
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
    # center "  Raydium LPs  " with rails on both sides
    t = f"  {title.strip()}  "
    fill = max(0, W - len(t))
    left = fill // 2
    right = fill - left
    return f"{ch * left}{t}{ch * right}"


def _abbr_middle(s: str, front: int = 4, back: int = 4, min_len: int = 12) -> str:
    if not isinstance(s, str):
        s = str(s)
    s = s.strip()
    if len(s) <= min_len or len(s) <= front + back + 3:
        return s
    return f"{s[:front]}…{s[-back:]}"


def _fmt_usd(v: Any) -> str:
    try:
        x = float(v)
        # No cents if near-integer; two decimals otherwise
        return f"${int(round(x)):,}" if abs(x - round(x)) < 1e-6 else f"${x:,.2f}"
    except Exception:
        return "—"


def _fmt_lp(v: Any) -> str:
    if v in (None, "", 0, 0.0):
        return "—"
    try:
        x = float(v)
        # Hide tiny noise; otherwise compact
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
    # Return h:mma/pm (lowercased) by default
    dt: Optional[_dt.datetime] = None
    if ts is None:
        dt = _dt.datetime.now()
    elif isinstance(ts, (int, float)):
        dt = _dt.datetime.fromtimestamp(float(ts))
    elif isinstance(ts, _dt.datetime):
        dt = ts
    elif isinstance(ts, str):
        s = ts.strip()
        try:
            if s.endswith("Z"):
                dt = _dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
            else:
                dt = _dt.datetime.fromisoformat(s)
        except Exception:
            dt = _dt.datetime.now()
    else:
        dt = _dt.datetime.now()

    hour = dt.strftime("%I").lstrip("0") or "0"
    return f"{hour}:{dt.strftime('%M%p').lower()}"


# ────────────────────────────────────────────────────────────────────────────────
# Data normalization
# ────────────────────────────────────────────────────────────────────────────────

def _norm_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a Raydium LP-like record into:
      { pool, address, lp_qty, usd_value, apr, checked_ts }
    Accept a variety of likely shapes.
    """
    if rec is None:
        rec = {}

    pool = (
        rec.get("pool")
        or rec.get("pool_name")
        or rec.get("amm")
        or rec.get("pair")
        or rec.get("symbol")
        or rec.get("collection")
        or ""
    )

    address = (
        rec.get("address")
        or rec.get("owner")
        or rec.get("pubkey")
        or rec.get("mint")  # NFT mint shown as address if nothing else
        or ""
    )

    lp_qty = rec.get("lp_qty") or rec.get("qty") or rec.get("balance") or rec.get("amount") or rec.get("raw_amount")
    usd_value = (
        rec.get("usd_value") or rec.get("usd") or rec.get("value_usd") or rec.get("fiat_value") or 0.0
    )
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
    """
    Try sources in order:
      1) ctx['records'] or ctx['raydium'] (list/dict)
      2) ctx['csum']['raydium']['records']
      3) dl.raydium.* helpers if available
    Return (records, source_label)
    """
    # 1) Direct
    direct = ctx.get("records")
    if isinstance(direct, list) and direct:
        return [ _norm_record(r or {}) for r in direct ], "ctx.records"

    rayd = ctx.get("raydium")
    if isinstance(rayd, list) and rayd:
        return [ _norm_record(r or {}) for r in rayd ], "ctx.raydium"

    if isinstance(rayd, dict):
        seq = rayd.get("records") or rayd.get("positions") or rayd.get("lps") or []
        if isinstance(seq, list) and seq:
            return [ _norm_record(r or {}) for r in seq ], "ctx.raydium.records"

    # 2) From csum tree
    csum = ctx.get("csum") or ctx.get("summary") or {}
    seq = _coalesce(
        (csum.get("raydium") or {}).get("records"),
        (csum.get("raydium") or {}).get("lps"),
        default=None,
    )
    if isinstance(seq, list) and seq:
        return [ _norm_record(r or {}) for r in seq ], "csum.raydium"

    # 3) From DataLocker provider if present
    dl = ctx.get("dl")
    provider = getattr(dl, "raydium", None)
    if provider:
        # Try common shapes
        for name in (
            "get_latest_lp_positions",
            "get_lp_positions",
            "get_positions",
            "list_lp_nfts",
            "list_positions",
        ):
            fn = getattr(provider, name, None)
            if callable(fn):
                try:
                    res = fn()
                    if isinstance(res, dict):
                        arr = (
                            res.get("records") or res.get("positions") or res.get("lps") or res.get("items") or []
                        )
                    else:
                        arr = res
                    if isinstance(arr, list) and arr:
                        return [ _norm_record(r or {}) for r in arr ], f"dl.raydium.{name}()"
                except Exception:
                    pass

        # Fall back to plain attributes
        for attr in ("records", "positions", "lps", "items"):
            arr = getattr(provider, attr, None)
            if isinstance(arr, list) and arr:
                return [ _norm_record(r or {}) for r in arr ], f"dl.raydium.{attr}"

    return [], "none"


# ────────────────────────────────────────────────────────────────────────────────
# Rendering
# ────────────────────────────────────────────────────────────────────────────────

def render(context: Optional[Dict[str, Any]] = None, **kwargs) -> List[str]:
    """
    Return a list[str] representing the Raydium panel block.
    Inputs may include:
      - dl: DataLocker
      - csum/summary: dict carrying raydium.records
      - records: explicit list of raw records
      - width: optional console width
    """
    ctx: Dict[str, Any] = {}
    if context:
        ctx.update(context)
    if kwargs:
        ctx.update(kwargs)

    width = ctx.get("width") or _console_width()

    # UI skeleton: title rail, header rule, table header
    out: List[str] = []
    out.append(_title_rail("Raydium LPs", width))
    out.append(_hr(width))  # solid rule above column headers

    # Column spec
    # match your other panels: left columns roomy; numbers right-aligned
    # Pool(22) Address(34) LP(9) USD(12) APR(7) Checked(10)  → keep within width
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
            f"{lp}{' ' * 2}"
            f"{usd}{' ' * 2}"
            f"{apr}{' ' * 2}"
            f"{chk}"
        )
        return line[:width] if len(line) > width else line

    header = fmt_row("Pool", "Address", "LP", "USD", "APR", "Checked")
    out.append(header)

    records, source = _collect_records(ctx)

    total_usd = 0.0
    last_ts = None

    if records:
        for rec in records:
            total_usd += float(rec.get("usd_value") or 0.0)
            ts = rec.get("checked_ts")
            if ts:
                last_ts = ts

            row = fmt_row(
                rec.get("pool", ""),
                rec.get("address", ""),
                _fmt_lp(rec.get("lp_qty")),
                _fmt_usd(rec.get("usd_value")),
                _fmt_apr(rec.get("apr")),
                _fmt_time(ts) if ts else "",
            )
            out.append(row)
    else:
        out.append("(no raydium positions)")

    # Totals line & checked stamp (aligned like your other panels)
    out.append("")
    total_line = f"  Total (USD): {_fmt_usd(total_usd)}"
    checked_line = f"  Checked: {_fmt_time(last_ts) if last_ts else _fmt_time(None)}"
    # render as two lines so it wraps clean on narrow consoles
    out.append(total_line if len(total_line) < width else total_line[: width - 1] + "…")
    out.append(checked_line)

    # Provenance (quiet one-liner, useful when debugging)
    out.append(f"[RAY] source={source} count={len(records)}")

    return out


def name() -> str:
    return PANEL_NAME


if __name__ == "__main__":
    demo = [
        {
            "pool": "So11111111111111111111111111111111111111112/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "address": "2jn9ve3KJb9yA2h5JW4fT5A9XxxM1e3qJ3kfdSU9pj",
            "lp_qty": 1.23456,
            "usd_value": 106,
            "apr": None,
            "checked_ts": _dt.datetime.now().isoformat(timespec="seconds"),
        }
    ]
    for ln in render(records=demo):
        print(ln)
