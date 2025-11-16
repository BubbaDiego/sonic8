from __future__ import annotations

import logging
from io import StringIO
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from rich.console import Console
from rich.table import Table
from rich import box

from backend.core.reporting_core.sonic_reporting.console_panels import data_access
from backend.core.reporting_core.sonic_reporting.positions_snapshot import (
    build_positions_snapshot,
)
from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_below,
    body_indent_lines,
    paint_line,
    color_if_plain,
)

try:
    from .theming import HR_WIDTH
except Exception:  # pragma: no cover
    HR_WIDTH = 100

log = logging.getLogger(__name__)

PANEL_SLUG = "positions"
PANEL_NAME = "Positions"

# Column labels (with icons in the header row only)
HEADER_LABELS = [
    "🪙 Asset",
    "📦 Size",
    "🟩 Value",
    "📈 PnL",
    "🧷 Lev",
    "💧 Liq",
    "🔥 Heat",
    "🧭 Trave",
]

# ──────────────────────────────────────────────────────────────────────────────
# Helpers copied from the old panel (but now used per‑column instead of
# building one big formatted string).
# ──────────────────────────────────────────────────────────────────────────────


def _to_mapping(x: Any) -> Mapping[str, Any]:
    if isinstance(x, Mapping):
        return x
    if hasattr(x, "__dict__"):
        return x.__dict__  # type: ignore[return-value]
    return {}


def _first(*vals: Any) -> Any:
    for v in vals:
        if v is not None:
            return v
    return None


def _num(x: Any) -> Optional[float]:
    try:
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            s = x.strip()
            if not s:
                return None
            s = s.replace("$", "").replace(",", "").replace("%", "").replace("×", "x")
            return float(s)
    except Exception:
        return None
    return None


def _fmt_money(v: Optional[float]) -> str:
    return f"${v:,.2f}" if isinstance(v, (int, float)) else "-"


def _fmt_pct(v: Optional[float]) -> str:
    return f"{v:.2f}%" if isinstance(v, (int, float)) else "-"


def _fmt_size(v: Optional[float]) -> str:
    return f"{v:,.2f}" if isinstance(v, (int, float)) else "-"


def _fmt_lev(v: Optional[float]) -> str:
    return f"{v:.2f}×" if isinstance(v, (int, float)) else "-"


def _fmt_travel(v: Optional[float]) -> str:
    return _fmt_pct(v)


def _compute_travel_pct(row: Mapping[str, Any]) -> Optional[float]:
    """
    Travel% comes from 'travel_percent' or 'travel'.
    """
    v = _first(row.get("travel_percent"), row.get("travel"))
    return _num(v)


def _compute_heat_pct(travel_pct: Optional[float]) -> Optional[float]:
    """
    Heat is a simple absolute move measure based on travel%.
    (Exact formula isn't critical for layout; we keep it stable.)
    """
    if travel_pct is None:
        return None
    return abs(travel_pct)


# Totals computation using the same fields we render
def _compute_totals_row(items: Iterable[Any]) -> Dict[str, str]:
    size = 0.0
    value = 0.0
    pnl = 0.0
    levs: List[float] = []
    travs: List[float] = []

    for it in items:
        d = _to_mapping(it)

        v = _num(d.get("size"))
        if v is not None:
            size += v

        v = _num(d.get("value"))
        if v is not None:
            value += v

        v = _num(_first(d.get("pnl_after_fees_usd"), d.get("pnl")))
        if v is not None:
            pnl += v

        v = _num(d.get("leverage"))
        if v is not None:
            levs.append(v)

        v = _compute_travel_pct(d)
        if v is not None:
            travs.append(v)

    avg_lev = sum(levs) / len(levs) if levs else None
    avg_trav = sum(travs) / len(travs) if travs else None

    return {
        "asset": "Totals",
        "size": _fmt_size(size if size != 0.0 else None),
        "value": _fmt_money(value if value != 0.0 else None),
        "pnl": _fmt_money(pnl if pnl != 0.0 else None),
        "lev": _fmt_lev(avg_lev),
        "liq": "-",
        "heat": "-",
        "trav": _fmt_travel(avg_trav),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Data access
# ──────────────────────────────────────────────────────────────────────────────


def _get_items_from_manager(context: dict | None) -> list[dict]:
    """
    Load live positions for the Positions panel.

    Priority:
      1) dl.positions.get_all_positions()  (new 2025 DL layer)
      2) legacy build_positions_snapshot() fallback
    """
    dl = data_access.dl_or_context(context)
    if dl is None:
        return []

    # ---- Primary: DataLocker.positions manager (new architecture) ----
    try:
        mgr = getattr(dl, "positions", None)
        if mgr is not None:
            # Prefer the rich helper if present
            getter = None
            for name in ("get_all_positions", "get_positions", "list", "get_all"):
                fn = getattr(mgr, name, None)
                if callable(fn):
                    getter = fn
                    break

            rows: list | None = None
            if getter is not None:
                try:
                    rows = getter()
                except TypeError:
                    # Some variants expect a dummy argument; best-effort call
                    try:
                        rows = getter(None)  # type: ignore[arg-type]
                    except Exception:
                        rows = None
            else:
                # Some DLPositionManager versions expose a .positions list
                raw = getattr(mgr, "positions", None)
                if isinstance(raw, list):
                    rows = raw

            if isinstance(rows, list) and rows:
                normalized: list[dict] = []
                for row in rows:
                    if isinstance(row, dict):
                        normalized.append(dict(row))
                    else:
                        # pydantic model / simple object → turn into dict
                        data = getattr(row, "model_dump", None)
                        if callable(data):
                            normalized.append(data())
                        else:
                            normalized.append(dict(getattr(row, "__dict__", {})))
                return normalized
    except Exception as exc:  # pragma: no cover - defensive only
        log.warning(f"[positions_panel] dl.positions lookup failed: {exc}")

    # ---- Fallback: legacy snapshot helper (older consoles / CLIs) ----
    try:
        snap = build_positions_snapshot()
        rows = snap.get("rows") or []
        if isinstance(rows, list):
            return rows
    except Exception as exc:  # pragma: no cover - defensive only
        log.warning(f"[positions_panel] snapshot fallback failed: {exc}")

    return []


# ──────────────────────────────────────────────────────────────────────────────
# Rich table plumbing
# ──────────────────────────────────────────────────────────────────────────────


def _resolve_table_cfg(body_cfg: Dict[str, Any]) -> Dict[str, Any]:
    tcfg = (body_cfg or {}).get("table") or {}
    style = str(tcfg.get("style") or "invisible").lower().strip()
    table_justify = str(tcfg.get("table_justify") or "left").lower().strip()
    header_justify = str(tcfg.get("header_justify") or "left").lower().strip()
    return {
        "style": style,
        "table_justify": table_justify,
        "header_justify": header_justify,
    }


def _style_to_box(style: str):
    style = (style or "").lower()
    if style == "thin":
        return box.SIMPLE_HEAD, False
    if style == "thick":
        return box.HEAVY_HEAD, True
    # "invisible" or unknown → no borders
    return None, False


def _justify_lines(lines: List[str], justify: str, width: int) -> List[str]:
    justify = (justify or "left").lower()
    out: List[str] = []
    for line in lines:
        s = line.rstrip("\n")
        pad = max(0, width - len(s))
        if justify == "right":
            out.append(" " * pad + s)
        elif justify == "center":
            left = pad // 2
            out.append(" " * left + s)
        else:
            out.append(s)
    return out


def _build_rich_table(items: List[Any], body_cfg: Dict[str, Any]) -> List[str]:
    table_cfg = _resolve_table_cfg(body_cfg)
    box_style, show_lines = _style_to_box(table_cfg["style"])

    table = Table(
        show_header=True,
        header_style="",
        show_lines=show_lines,
        box=box_style,
        pad_edge=False,
        expand=False,
    )

    # Columns (headers with icons)
    table.add_column(HEADER_LABELS[0], justify="left", no_wrap=True)
    table.add_column(HEADER_LABELS[1], justify="right")
    table.add_column(HEADER_LABELS[2], justify="right")
    table.add_column(HEADER_LABELS[3], justify="right")
    table.add_column(HEADER_LABELS[4], justify="right")
    table.add_column(HEADER_LABELS[5], justify="right")
    table.add_column(HEADER_LABELS[6], justify="right")
    table.add_column(HEADER_LABELS[7], justify="right")

    # Body rows
    for it in items:
        d = _to_mapping(it)
        asset = str(d.get("asset") or d.get("symbol") or "-")
        size = _fmt_size(_num(d.get("size")))
        value = _fmt_money(_num(d.get("value")))
        pnl = _fmt_money(_num(_first(d.get("pnl_after_fees_usd"), d.get("pnl"))))
        lev = _fmt_lev(_num(d.get("leverage")))
        liq = _fmt_pct(_num(d.get("liq_pct") or d.get("liq")))
        travel_pct = _compute_travel_pct(d)
        heat = _fmt_pct(_compute_heat_pct(travel_pct))
        trav = _fmt_travel(travel_pct)

        table.add_row(asset, size, value, pnl, lev, liq, heat, trav)

    # Totals row
    totals = _compute_totals_row(items)
    table.add_row(
        totals["asset"],
        totals["size"],
        totals["value"],
        totals["pnl"],
        totals["lev"],
        totals["liq"],
        totals["heat"],
        totals["trav"],
    )

    buf = StringIO()
    console = Console(record=True, width=HR_WIDTH, file=buf, force_terminal=True)
    console.print(table)
    text = console.export_text().rstrip("\n")
    if not text:
        return []

    raw_lines = text.splitlines()
    return _justify_lines(raw_lines, table_cfg["table_justify"], HR_WIDTH)


# ──────────────────────────────────────────────────────────────────────────────
# Public render entrypoint
# ──────────────────────────────────────────────────────────────────────────────


def render(context: Any, width: Optional[int] = None) -> List[str]:
    body_cfg = get_panel_body_config(PANEL_SLUG)
    title_block = emit_title_block(PANEL_SLUG, PANEL_NAME)

    items = _get_items_from_manager(context)

    lines: List[str] = []
    lines.extend(title_block)

    if not items:
        header = "  ".join(HEADER_LABELS)
        lines.extend(
            body_indent_lines(
                PANEL_SLUG,
                [
                    paint_line(header, body_cfg.get("column_header_text_color", "")),
                    "(no positions)",
                ],
            )
        )
        lines.extend(body_pad_below(PANEL_SLUG))
        return lines

    table_lines = _build_rich_table(items, body_cfg)

    if table_lines:
        header_line = table_lines[0]
        data_lines = table_lines[1:]

        totals_color = body_cfg.get("totals_row_color", "grey50")

        # Header
        lines.extend(
            body_indent_lines(
                PANEL_SLUG,
                [paint_line(header_line, body_cfg.get("column_header_text_color", ""))],
            )
        )

        # Body rows: all except last
        if data_lines:
            body_rows = data_lines[:-1]
            totals_row = data_lines[-1]
        else:
            body_rows = []
            totals_row = ""

        for ln in body_rows:
            lines.extend(
                body_indent_lines(
                    PANEL_SLUG,
                    [color_if_plain(ln, body_cfg.get("body_text_color", ""))],
                )
            )

        # Totals row tinted separately
        if totals_row:
            lines.extend(
                body_indent_lines(
                    PANEL_SLUG,
                    [paint_line(totals_row, totals_color)],
                )
            )
    else:
        lines.extend(body_indent_lines(PANEL_SLUG, ["(no positions)"]))

    lines.extend(body_pad_below(PANEL_SLUG))
    return lines
