# -*- coding: utf-8 -*-
"""Market Alerts panel."""
from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_below,
    body_indent_lines,
    color_if_plain,
)

PANEL_SLUG = "market"
PANEL_NAME = "Market Alerts"


def _resolve_dl(ctx: Any) -> Any:
    if ctx is None:
        return None
    if isinstance(ctx, dict):
        dl = ctx.get("dl")
        if dl is not None:
            return dl
    return getattr(ctx, "dl", None)


def _get_monitor_rows(dl: Any) -> List[Dict[str, Any]]:
    """
    Robustly pull monitor rows from dl.monitors / dl_dl_monitors.

    This is your original logic – DO NOT TOUCH – it already works.
    """
    if dl is None:
        return []
    mgr = getattr(dl, "monitors", None) or getattr(dl, "dl_monitors", None)
    if mgr is None:
        return []

    candidates: Iterable[Any] = []
    for name in (
        "select_all",
        "list_all",
        "all",
        "latest",
        "list_latest",
        "latest_rows",
        "get_latest",
    ):
        fn = getattr(mgr, name, None)
        if callable(fn):
            try:
                data = fn()
            except TypeError:
                continue
            if data:
                candidates = data
                break
    else:
        direct = getattr(mgr, "rows", None)
        if direct:
            candidates = direct

    rows: List[Dict[str, Any]] = []
    for row in candidates:
        if isinstance(row, dict):
            rows.append(dict(row))
            continue
        norm: Dict[str, Any] = {}
        for key in (
            "monitor",
            "label",
            "state",
            "value",
            "unit",
            "thr_op",
            "thr_value",
            "thr_unit",
            "source",
            "meta",
        ):
            if hasattr(row, key):
                norm[key] = getattr(row, key)
        rows.append(norm)
    return rows


def _normalize_meta(meta: Any) -> Dict[str, Any]:
    if isinstance(meta, dict):
        return dict(meta)
    if isinstance(meta, str):
        try:
            data = json.loads(meta)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _market_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        monitor = (row.get("monitor") or "").lower()
        if monitor != "market":
            continue
        row = dict(row)
        row["meta"] = _normalize_meta(row.get("meta"))
        out.append(row)
    return out


# ===== value formatting helpers =====

def _fmt_price(val: Any) -> str:
    if val is None:
        return "–".rjust(8)
    try:
        return f"{float(val):>8.2f}"
    except Exception:
        return f"{str(val)[:8]:>8}"


def _fmt_move(val: Any) -> str:
    if val is None:
        return "–".rjust(8)
    try:
        v = float(val)
        sign = "+" if v >= 0 else ""
        return f"{sign}{v:>7.2f}"
    except Exception:
        return f"{str(val)[:8]:>8}"


def _fmt_pct(val: Any) -> str:
    if val is None:
        return "–".rjust(8)
    try:
        v = float(val)
        sign = "+" if v >= 0 else ""
        return f"{sign}{v:>6.2f}%"
    except Exception:
        return f"{str(val)[:8]:>8}"


def _fmt_threshold(meta: Dict[str, Any], thr_value: Any) -> str:
    # Prefer explicit description if present
    desc = meta.get("threshold_desc") or meta.get("desc")
    if isinstance(desc, str) and desc.strip():
        txt = desc.strip()
    else:
        try:
            v = float(thr_value)
            txt = f"${v:.2f} move"
        except Exception:
            txt = str(thr_value or "–")
    if len(txt) > 14:
        return txt[:13] + "…"
    return txt.ljust(14)


def _fmt_bar(meta: Dict[str, Any]) -> str:
    try:
        prox = float(meta.get("proximity") or 0.0)
    except Exception:
        prox = 0.0
    prox = max(0.0, min(prox, 1.0))
    filled = int(round(prox * 10))
    filled = max(0, min(filled, 10))
    return "▰" * filled + "▱" * (10 - filled)


def _asset_from_row(row: Dict[str, Any]) -> str:
    meta = row.get("meta") or {}
    asset = row.get("asset") or meta.get("asset") or row.get("label") or ""
    asset = str(asset).strip()
    if not asset:
        return "—"
    return asset[:5].ljust(5)


def _entry_price(meta: Dict[str, Any]) -> Any:
    """
    Entry (anchor) price:
      • Prefer meta["anchor_price"] or meta["entry_price"] if present.
      • Else, derive from price - move_abs if both exist.
    """
    anchor = meta.get("anchor_price") or meta.get("entry_price")
    if anchor is not None:
        return anchor

    price = meta.get("price") or meta.get("current_price")
    move_abs = meta.get("move_abs")
    try:
        if price is not None and move_abs is not None:
            return float(price) - float(move_abs)
    except Exception:
        pass
    return None


def _current_price(meta: Dict[str, Any]) -> Any:
    return meta.get("price") or meta.get("current_price")


def _move_abs(meta: Dict[str, Any]) -> Any:
    mv = meta.get("move_abs")
    if mv is not None:
        return mv
    # derive from price / entry if needed
    price = meta.get("price") or meta.get("current_price")
    anchor = _entry_price(meta)
    try:
        if price is not None and anchor is not None:
            return float(price) - float(anchor)
    except Exception:
        pass
    return None


def _move_pct(meta: Dict[str, Any]) -> Any:
    mv = meta.get("move_pct")
    if mv is not None:
        return mv
    price = meta.get("price") or meta.get("current_price")
    anchor = _entry_price(meta)
    try:
        if price is not None and anchor not in (None, 0):
            return (float(price) - float(anchor)) / float(anchor) * 100.0
    except Exception:
        pass
    return None


def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    dl = _resolve_dl(context)
    body_cfg = get_panel_body_config(PANEL_SLUG)
    lines: List[str] = []

    # title
    lines += emit_title_block(PANEL_SLUG, PANEL_NAME)

    if dl is None:
        note = color_if_plain(
            "  (no DataLocker context)",
            body_cfg["body_text_color"],
        )
        lines += body_indent_lines(PANEL_SLUG, [note])
        lines += body_pad_below(PANEL_SLUG)
        return lines

    rows = _market_rows(_get_monitor_rows(dl))

    # header with icon + label columns
    header = (
        "  🪙  Asset   "
        "💵  Entry     "
        "💹  Current   "
        "📉  Move      "
        "📊  Move%     "
        "🎯  Thr              "
        "🔋  Prox        "
        "🧾  State"
    )
    header_colored = color_if_plain(header, body_cfg["column_header_text_color"])
    lines += body_indent_lines(PANEL_SLUG, [header_colored])

    if not rows:
        note = color_if_plain(
            "  (no active market alerts)",
            body_cfg["body_text_color"],
        )
        lines += body_indent_lines(PANEL_SLUG, [note])
        lines += body_pad_below(PANEL_SLUG)
        return lines

    # data rows
    for row in rows:
        meta = row.get("meta") or {}
        asset = _asset_from_row(row)

        entry = _entry_price(meta)
        current = _current_price(meta)
        move_abs = _move_abs(meta)
        move_pct = _move_pct(meta)

        thr_val = row.get("thr_value")
        bar = _fmt_bar(meta)
        state = str(row.get("state") or "").upper()

        line = (
            f"  🪙  {asset:<5}  "
            f"💵  {_fmt_price(entry)}  "
            f"💹  {_fmt_price(current)}  "
            f"📉  {_fmt_move(move_abs)}  "
            f"📊  {_fmt_pct(move_pct)}  "
            f"🎯  {_fmt_threshold(meta, thr_val)}  "
            f"🔋  {bar:<10}  "
            f"🧾  {state:<7}"
        )

        lines += body_indent_lines(
            PANEL_SLUG,
            [color_if_plain(line, body_cfg["body_text_color"])],
        )

    lines += body_pad_below(PANEL_SLUG)
    return lines


def connector(dl=None, ctx: Optional[Dict[str, Any]] = None, width: Optional[int] = None) -> List[str]:
    context: Dict[str, Any] = dict(ctx or {})
    if dl is not None:
        context.setdefault("dl", dl)
    return render(context, width=width)
