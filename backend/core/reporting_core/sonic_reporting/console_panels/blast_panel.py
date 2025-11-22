from __future__ import annotations

from typing import Any, Dict, Iterable, List

from . import data_access
from .theming import console_width, hr, title_lines

PANEL_SLUG = "blast"
PANEL_NAME = "Blast Radius"
PANEL_ICON = "💥"


def _resolve_dl(ctx: Any) -> Any:
    try:
        return data_access.dl_or_context(ctx)
    except Exception:
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
            "asset",
            "state",
            "value",
            "unit",
            "threshold",
            "thr_value",
            "source",
            "meta",
        ):
            if hasattr(row, key):
                norm[key] = getattr(row, key)
        rows.append(norm)
    return rows


def _latest_blast_by_asset(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        monitor = (row.get("monitor") or "").lower()
        if monitor != "blast":
            continue
        asset = (row.get("asset") or row.get("label") or "-").upper()
        latest[asset] = row
    return latest


def _fmt_float(val: Any) -> float:
    try:
        return float(val)
    except Exception:
        return 0.0


def render(ctx: Dict[str, Any] | None = None, width: int | None = None) -> List[str]:
    dl = _resolve_dl(ctx)
    rows = _get_monitor_rows(dl)
    latest = _latest_blast_by_asset(rows)
    width = width or console_width()

    if not latest:
        return [f"[{PANEL_SLUG}] no blast radius data"]

    lines: List[str] = []
    lines.extend(title_lines(PANEL_NAME, icon=PANEL_ICON, width=width))

    header = f"{'Asset':6} {'Enc%':>7} {'Alert%':>7} {'LDist':>8} {'BR':>8} {'Travel%':>9} {'State':>8}"
    lines.append(header)
    lines.append(hr(width=len(header)))

    for asset, row in sorted(latest.items()):
        val = _fmt_float(row.get("value"))
        threshold = row.get("threshold") or {}
        if isinstance(threshold, dict):
            thr_val = threshold.get("value")
        else:
            thr_val = threshold
        thr = _fmt_float(thr_val)
        meta = row.get("meta") or {}
        ld = _fmt_float(meta.get("liq_distance"))
        br = _fmt_float(meta.get("blast_radius"))
        travel = _fmt_float(meta.get("travel_pct")) if meta.get("travel_pct") is not None else 0.0
        state = (row.get("state") or "OK").upper()

        lines.append(
            f"{asset:6} {val:7.2f} {thr:7.2f} {ld:8.2f} {br:8.2f} {travel:9.2f} {state:>8}"
        )

    return lines


def connector(dl=None, ctx: Dict[str, Any] | None = None, width: int | None = None):
    context = ctx or {}
    if isinstance(context, dict) and dl is not None:
        context.setdefault("dl", dl)
    return render(context, width=width)
