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


def _format_value(value: Any) -> str:
    try:
        return f"{float(value):>8.2f}"
    except Exception:
        return f"{str(value or '—'):>8}"


def _format_threshold(value: Any) -> str:
    try:
        return f"{float(value):>8.2f}"
    except Exception:
        return f"{str(value or '—'):>8}"


def _format_desc(meta: Dict[str, Any]) -> str:
    desc = (meta.get("threshold_desc") or meta.get("desc") or "")
    desc = str(desc)
    if len(desc) > 22:
        return desc[:21] + "…"
    return desc.ljust(22)


def _format_bar(meta: Dict[str, Any]) -> str:
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


def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    dl = _resolve_dl(context)
    body_cfg = get_panel_body_config(PANEL_SLUG)
    lines: List[str] = []

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

    if not rows:
        note = color_if_plain(
            "  (no active market alerts)",
            body_cfg["body_text_color"],
        )
        lines += body_indent_lines(PANEL_SLUG, [note])
        lines += body_pad_below(PANEL_SLUG)
        return lines

    header = color_if_plain(
        "  🪙Asset  📊Value      🎯Thr     Desc                   🔋Prox   State",
        body_cfg["column_header_text_color"],
    )
    lines += body_indent_lines(PANEL_SLUG, [header])

    for row in rows:
        meta = row.get("meta") or {}
        line = "  {asset} {value}  {thr}  {desc} {bar} {state:<6}".format(
            asset=_asset_from_row(row),
            value=_format_value(row.get("value")),
            thr=_format_threshold(row.get("thr_value")),
            desc=_format_desc(meta),
            bar=_format_bar(meta),
            state=str(row.get("state") or "").upper(),
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
