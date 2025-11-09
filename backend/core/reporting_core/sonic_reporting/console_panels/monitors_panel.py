from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .theming import (
    console_width as _theme_width,
    hr as _theme_hr,
    title_lines as _theme_title,
    want_outer_hr,
)

PANEL_KEY = "monitors_panel"
PANEL_NAME = "Monitors"
PANEL_SLUG = "monitors"

# Icons for enabled/disabled and status; fall back to plain text if terminals are grumpy.
ICON_ENABLED = os.getenv("SONIC_ICON_ENABLED", "✅")
ICON_DISABLED = os.getenv("SONIC_ICON_DISABLED", "◻️")
ICON_OK = os.getenv("SONIC_ICON_OK", "🟩")
ICON_WARN = os.getenv("SONIC_ICON_WARN", "🟨")
ICON_ERR = os.getenv("SONIC_ICON_ERR", "🟥")

# Order and friendly names for common monitors; unknown keys will be appended in alpha order.
_MONITOR_ORDER = [
    "sonic",      # umbrella / heartbeat group if present
    "liquid",
    "profit",
    "market",
    "price",
    "xcom",
]
_MONITOR_LABELS = {
    "sonic": "Sonic",
    "liquid": "Liquid",
    "profit": "Profit",
    "market": "Market",
    "price": "Price",
    "xcom": "XCom",
}


def _console_width(default: int = 92) -> int:
    return _theme_width(default)


def _hr(width: Optional[int] = None, ch: str = "─") -> str:
    return _theme_hr(width, ch)


def _safe_dict(d: Any) -> Dict[str, Any]:
    return d if isinstance(d, dict) else {}


def _enabled_map(context: Dict[str, Any]) -> Dict[str, bool]:
    """
    Expected sources (any may exist):
      - context["csum"]["monitors_enabled"] : {"liquid": True, "profit": False, ...}
      - context["monitors_enabled"]
      - context["config"]["monitor"]["enabled"]
    We merge truthy values; missing keys default to False.
    """
    csum = _safe_dict(context.get("csum"))
    enabled = {}
    # priority: csum -> top-level -> config
    enabled.update(_safe_dict(csum.get("monitors_enabled")))
    enabled.update(_safe_dict(context.get("monitors_enabled")))
    cfg_enabled = _safe_dict(_safe_dict(context.get("config")).get("monitor", {})).get("enabled")
    enabled.update(_safe_dict(cfg_enabled))

    # boolean-cast
    return {k: bool(v) for k, v in enabled.items()}


def _status_summary(context: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    """
    Gather per-monitor counts by status bucket. We try a few shapes:
      - context["csum"]["monitors"]: { "liquid": {"ok": 3, "warn": 1, "err": 0}, ... }
      - context["monitors"]: same shape
      - context["monitor_status"]: array/dict -> we reduce to ok/warn/err
    If nothing is available, return {} and the panel will only show enabled toggles.
    """
    csum = _safe_dict(context.get("csum"))
    src = (
        _safe_dict(csum.get("monitors"))
        or _safe_dict(context.get("monitors"))
        or _safe_dict(context.get("monitor_status"))
    )

    # Normalize to {name: {ok, warn, err}}
    norm: Dict[str, Dict[str, int]] = {}
    for name, payload in _safe_dict(src).items():
        if isinstance(payload, dict):
            ok = int(payload.get("ok", 0))
            warn = int(payload.get("warn", 0))
            err = int(payload.get("err", 0))
        else:
            # Fallback: unknown shape → put everything as ok=0/warn=0/err=0
            ok = warn = err = 0
        norm[name] = {"ok": ok, "warn": warn, "err": err}
    return norm


def _row_enabled(name: str, enabled: bool, label: str) -> str:
    box = ICON_ENABLED if enabled else ICON_DISABLED
    return f"  {box} {label}"


def _row_status(counts: Dict[str, int]) -> str:
    ok = counts.get("ok", 0)
    warn = counts.get("warn", 0)
    err = counts.get("err", 0)
    parts: List[str] = []
    # Only show buckets that are nonzero to reduce noise; if all zero, show 0 OK.
    if ok or (not warn and not err):
        parts.append(f"{ICON_OK} {ok}")
    if warn:
        parts.append(f"{ICON_WARN} {warn}")
    if err:
        parts.append(f"{ICON_ERR} {err}")
    return "  ".join(parts)


def _sorted_monitor_keys(enabled_map: Dict[str, bool], status: Dict[str, Dict[str, int]]) -> List[str]:
    keys = set(enabled_map.keys()) | set(status.keys())
    ordered = [k for k in _MONITOR_ORDER if k in keys]
    tail = sorted(keys - set(ordered))
    return ordered + tail


def render_lines(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    """
    Public entrypoint for console_reporter panel stack.
    Returns a list[str] safe to print directly.
    """
    W = width or _console_width()
    out: List[str] = []

    wrap = want_outer_hr(PANEL_SLUG, default_string=PANEL_NAME)
    if wrap:
        out.append(_hr(W))
    out.extend(_theme_title(PANEL_SLUG, PANEL_NAME, width=W))
    if wrap:
        out.append(_hr(W))

    enabled_map = _enabled_map(context)
    status = _status_summary(context)

    if not enabled_map and not status:
        out.append("  (no monitor data)")
        return out
    # If we only have toggles, still print the table

    # Table header
    out.append("")
    out.append(f"{'Monitor':<18} {'Enabled':<10} Status")
    out.append("-" * W)

    for key in _sorted_monitor_keys(enabled_map, status):
        label = _MONITOR_LABELS.get(key, key.capitalize())
        is_on = bool(enabled_map.get(key, False))
        counts = status.get(key, {})
        left = f"{label:<18}"
        mid = f"{('ON' if is_on else 'OFF'):<10}"
        right = _row_status(counts)
        # Also show a checkbox line under each row for quick scanning
        out.append(f"{left} {mid} {right}")
        out.append(_row_enabled(key, is_on, label))

    # Panel footer spacing
    out.append("")
    return out


# Optional alias used by reporter stacks that import .render
def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    return render_lines(context, width)
