from __future__ import annotations

from typing import Any, Dict, List, Optional

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_below,
    body_indent_lines,
    color_if_plain,
)

PANEL_SLUG = "market"
PANEL_NAME = "Market Alerts"


def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    dl = context.get("dl")
    body_cfg = get_panel_body_config(PANEL_SLUG)

    lines: List[str] = []
    lines += emit_title_block(PANEL_SLUG, PANEL_NAME)

    if dl is None:
        lines += body_indent_lines(
            PANEL_SLUG,
            [color_if_plain("  (no DataLocker context)", body_cfg["body_text_color"])],
        )
        lines += body_pad_below(PANEL_SLUG)
        return lines

    # pull market monitor rows
    rows = []
    for r in dl.monitors.select_all():
        if r.get("monitor") == "market":
            rows.append(r)

    if not rows:
        lines += body_indent_lines(
            PANEL_SLUG,
            [color_if_plain("  (no active market alerts)", body_cfg["body_text_color"])],
        )
        lines += body_pad_below(PANEL_SLUG)
        return lines

    lines += body_indent_lines(
        PANEL_SLUG,
        [
            color_if_plain(
                "  Asset  Value      Thr      Desc                  Proximity   State",
                body_cfg["column_header_text_color"],
            )
        ],
    )

    for r in rows:
        meta = r.get("meta") or {}
        prox = float(meta.get("proximity") or 0.0)
        prox = max(0.0, min(prox, 1.0))
        filled = int(round(prox * 10))
        bar = "▰" * filled + "▱" * (10 - filled)

        asset = (r.get("asset") or "")[:5]
        value = float(r.get("value") or 0.0)
        thr = float(r.get("thr_value") or 0.0)
        desc = (meta.get("threshold_desc") or "")[:22]
        state = r.get("state") or ""

        line = (
            f"  {asset:<5} {value:>7.2f}  {thr:>7.2f}  "
            f"{desc:<22} {bar} {state:<6}"
        )
        lines += body_indent_lines(
            PANEL_SLUG,
            [color_if_plain(line, body_cfg["body_text_color"])],
        )

    lines += body_pad_below(PANEL_SLUG)
    return lines


def connector(*args, **kwargs) -> List[str]:
    return render(*args, **kwargs)
