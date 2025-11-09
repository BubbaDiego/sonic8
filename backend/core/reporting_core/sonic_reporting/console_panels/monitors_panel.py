from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional

from .theming import (
    console_width as _theme_width,
    title_lines as _theme_title,
    get_panel_body_config,
    color_if_plain,
    paint_line,
    body_pad_below,
    body_indent_lines,
)

PANEL_KEY = "monitors_panel"
PANEL_NAME = "Monitors"
PANEL_SLUG = "monitors"

ICON_OK = os.getenv("ICON_OK", "🟩")
ICON_WARN = os.getenv("ICON_WARN", "🟨")
ICON_ERR = os.getenv("ICON_ERR", "🟥")


def _safe_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _as_str(x: Any) -> str:
    if x is None:
        return "-"
    return str(x)


def _first_nonempty(*vals):
    for v in vals:
        if v not in (None, "", [], {}, ()):  # pragma: no cover - simple guard
            return v
    return None


# --- data sourcing -----------------------------------------------------------


def _from_legacy_rows(obj: Any) -> Optional[List[Dict[str, Any]]]:
    """Look for pre-flattened monitor rows in a few historical keys."""
    cand = _first_nonempty(
        _safe_dict(obj).get("monitor_rows"),
        _safe_dict(obj).get("monitors_table"),
        _safe_dict(obj).get("monitor_table"),
    )
    if isinstance(cand, list) and cand and isinstance(cand[0], dict):
        return cand
    return None


def _from_dl(context: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Ask DataLocker helpers for a monitors table if available."""
    dl = context.get("dl")
    if not dl:
        return None
    for name in ("get_monitor_rows", "get_monitors_table", "get_monitor_table"):
        fn = getattr(dl, name, None)
        if callable(fn):
            try:
                rows = fn()
                if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                    return rows
            except Exception:
                pass
    return None


def _from_csum(context: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Rehydrate monitor rows from the summary object when possible."""
    csum = _safe_dict(context.get("csum"))
    cand = _first_nonempty(
        csum.get("monitors_detail"),
        csum.get("monitors_items"),
        csum.get("monitor_rows"),
        csum.get("monitors_table"),
    )
    if isinstance(cand, list) and cand and isinstance(cand[0], dict):
        return cand
    return None


def _iter_checks(context: Dict[str, Any]) -> Iterable[Dict[str, str]]:
    rows = (
        _from_legacy_rows(context)
        or _from_csum(context)
        or _from_dl(context)
    )
    if not rows:
        return []

    normed: List[Dict[str, str]] = []
    for r in rows:
        d = _safe_dict(r)
        mon = _as_str(
            _first_nonempty(d.get("mon"), d.get("name"), d.get("monitor"), d.get("label"))
        )
        thresh = _as_str(_first_nonempty(d.get("thresh"), d.get("threshold")))
        value = _as_str(d.get("value"))
        state = _as_str(d.get("state"))
        age = _as_str(_first_nonempty(d.get("age"), d.get("age_s"), d.get("age_str")))
        src = _as_str(
            _first_nonempty(d.get("source"), d.get("src"), d.get("origin"), d.get("monitor_key"))
        )
        normed.append(
            {
                "mon": mon,
                "thresh": thresh,
                "value": value,
                "state": state,
                "age": age,
                "source": src,
            }
        )
    return normed


# --- render ------------------------------------------------------------------


def _clip(text: str, width: int) -> str:
    return text if len(text) <= width else text[:width]


def _format_state(raw: str) -> str:
    if not raw:
        return "-"
    upper = raw.upper()
    if upper.startswith("OK"):
        return f"{ICON_OK} {raw}"
    if upper.startswith("WARN"):
        return f"{ICON_WARN} {raw}"
    return f"{ICON_ERR} {raw}"


def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    W = width or _theme_width()
    out: List[str] = []

    out.extend(_theme_title(PANEL_SLUG, PANEL_NAME, width=W))
    body_cfg = get_panel_body_config(PANEL_SLUG)

    header = f"{'Monitor':<22} {'Thresh':>8}  {'Value':>8}  {'State':>7}  {'Age':>6}  {'Source'}"
    out.extend(
        body_indent_lines(
            PANEL_SLUG, [paint_line(_clip(header, W), body_cfg["column_header_text_color"])]
        )
    )

    divider = "-" * min(W, max(len(header), 10))
    out.extend(body_indent_lines(PANEL_SLUG, [_clip(divider, W)]))

    rows = list(_iter_checks(context))
    if rows:
        body_lines: List[str] = []
        for row in rows:
            state = _format_state(row.get("state", ""))
            left = f"{row['mon']:<22}"
            col2 = f"{row['thresh']:>8}"
            col3 = f"{row['value']:>8}"
            col4 = f"{state:>7}"
            col5 = f"{row['age']:>6}"
            col6 = row.get("source") or "-"
            line = f"{left} {col2}  {col3}  {col4}  {col5}  {col6}"
            body_lines.append(color_if_plain(_clip(line, W), body_cfg["body_text_color"]))
        out.extend(body_indent_lines(PANEL_SLUG, body_lines))
    else:
        msg = color_if_plain("(no monitor checks)", body_cfg["body_text_color"])
        out.extend(body_indent_lines(PANEL_SLUG, [msg]))

    out.extend(body_pad_below(PANEL_SLUG))
    return out
