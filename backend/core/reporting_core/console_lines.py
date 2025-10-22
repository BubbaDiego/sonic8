import datetime
import os
from typing import Dict, Any, List, Tuple, Optional, Mapping


from __future__ import annotations

# Compatibility shim: route all console output through the updated reporter.
from backend.core.reporting_core.console_reporter import (  # noqa: F401
    StrictWhitelistFilter,
    install_strict_console_filter,
    neuter_legacy_console_logger,
    silence_legacy_console_loggers,
    emit_compact_cycle,
    emit_sources_line,
    emit_json_summary,
)

_GREEN = "\x1b[32m"
_YELLOW = "\x1b[33m"
_RED = "\x1b[31m"
_CYAN = "\x1b[36m"
_DIM = "\x1b[90m"
_RESET = "\x1b[0m"


def _monitor_items_per_line() -> int:
    value = os.getenv("SONIC_MONITOR_TUPLES_PER_LINE", "4")
    try:
        parsed = int(value)
        return parsed if parsed > 0 else 4
    except (TypeError, ValueError):
        return 4


def _format_number(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number) >= 100:
        return f"{number:.0f}"
    return f"{number:.1f}"


def _format_monitor_items(items: Any, *, max_items: int = 4) -> str:
    if not items:
        return "—"
    if isinstance(items, str):
        return items
    if not isinstance(items, list):
        return str(items)

    tokens: List[str] = []
    for idx, item in enumerate(items):
        if idx >= max_items:
            tokens.append("…")
            break
        if isinstance(item, str):
            tokens.append(item)
            continue
        if isinstance(item, Mapping):
            tag = (
                item.get("tag")
                or item.get("label")
                or item.get("name")
                or item.get("asset")
                or item.get("symbol")
            )
            tag_str = str(tag) if tag not in (None, "") else "item"
            thr = _format_number(
                item.get("threshold")
                or item.get("threshold_pct")
                or item.get("threshold_value")
            )
            val = _format_number(
                item.get("value")
                or item.get("value_pct")
                or item.get("distance")
                or item.get("dist_pct")
            )
            segments: List[str] = []
            if thr is not None:
                segments.append(f"T={thr}")
            if val is not None:
                segments.append(f"V={val}")
            meta = item.get("meta")
            if isinstance(meta, str) and meta:
                segments.append(meta)
            severity = item.get("severity")
            if severity and str(severity).lower() not in {"pass", "ok"}:
                segments.append(str(severity))
            details = ", ".join(segments)
            if details:
                tokens.append(f"({tag_str}, {details})")
            else:
                tokens.append(str(tag_str))
            continue
        tokens.append(str(item))

    return "  ".join(tokens) if tokens else "—"


def _emit_monitor_lines(monitor_map: Dict[str, Any], *, max_items: int = 4) -> None:
    order = [
        ("liquid", "Liquid"),
        ("profit", "Profit"),
        ("market", "Market"),
        ("price", "Price"),
    ]
    for key, label in order:
        items = monitor_map.get(key) if isinstance(monitor_map, Mapping) else None
        line = _format_monitor_items(items or [], max_items=max_items)
        print(f"      {label:<7}: {line}")


# Price & position icons by ticker symbol for quick visual parsing in the console.
_PX_ICON = {"BTC": "🟡", "ETH": "🔷", "SOL": "🟣"}

def _fmt_short_clock(iso: Optional[str]) -> str:
    if not iso:
        return "–"
    try:
        value = iso
        if value.endswith("Z"):
            dt = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            dt = datetime.datetime.fromisoformat(value)
        local = dt.astimezone()
        # Windows-friendly format (no %-I)
        return local.strftime("%I:%M%p").lstrip("0").lower()
    except Exception:
        return "–"

def _prices_line(
    top3: List[Tuple[str, float]],
    ages: Optional[Dict[str, int]] = None,
    *,
    enable_color: bool = False,
) -> str:
    if not top3:
        return "–"
    parts: List[str] = []
    for symbol, price in top3:
        icon = _PX_ICON.get(symbol, symbol)
        value = f"${price:,.2f}"
        if enable_color:
            age = (ages or {}).get(symbol, 999_999)
            if age == 0:
                value = f"{_GREEN}{value}{_RESET}"
            elif 2 <= age <= 3:
                value = f"{_YELLOW}{value}{_RESET}"
            elif age > 3:
                value = f"{_RED}{value}{_RESET}"
        parts.append(f"{icon} {value}")
    return "  ".join(parts)

def emit_compact_cycle(
    summary: Dict[str, Any],
    cfg: Dict[str, Any],
    poll_interval_s: int,
    *,
    enable_color: bool = False,
) -> None:
    """
    Sonic6-compatible compact endcap driven by the classic `summary` dict.
    Expected keys (all optional with safe fallbacks):
      prices_top3, price_ages, prices_updated_at,
      positions_line, positions_updated_at, positions_brief,
      hedge_groups, elapsed_s, cycle_num, notifications_brief
    """
    _ = cfg  # placeholder for future config-specific rendering tweaks
    cycle_number = summary.get("cycle_num", "?")

    # ----- Centered Cyclone banner -----
    total_elapsed = float(summary.get("elapsed_s") or 0.0)
    elapsed_label = f"{_GREEN}✅{_RESET} {int(total_elapsed):d}s"

    banner = " 🌀🌀🌀  Cyclone Summary  🌀🌀🌀 "
    width = 78
    pad = max(0, (width - len(banner)) // 2)
    print(" " * pad + banner)

    # Time line under the banner
    print(f"   {_CYAN}Time{_RESET}     : {elapsed_label}", flush=True)

    # Prices
    prices_when = _fmt_short_clock(summary.get("prices_updated_at"))
    print(
        f"   {_CYAN}Prices{_RESET}   : "
        f"{_prices_line(summary.get('prices_top3', []), summary.get('price_ages', {}), enable_color=enable_color)}  • @ {prices_when}"
    )

    # Positions — show iconified line (e.g., 🟡 BTC-S, 🔷 ETH-L, 🟣 SOL-S)
    pos_when = _fmt_short_clock(summary.get("positions_updated_at"))
    pos_line = summary.get("positions_icon_line") or "–"
    pos_error = summary.get("positions_error")
    if pos_error:
        print(f"   {_CYAN}Positions{_RESET}: {pos_line}  • @ {pos_when} — {_RED}{pos_error}{_RESET}")
    else:
        print(f"   {_CYAN}Positions{_RESET}: {pos_line}  • @ {pos_when}")

    # Hedges
    hc = int(summary.get("hedge_groups", 0) or 0)
    print(f"   {_CYAN}Hedges{_RESET}   : {(''.join('🦔' for _ in range(hc))) if hc > 0 else '–'}")

    # Monitors + Alerts + Notifications
    monitor_map = summary.get("monitor_lines")
    if not isinstance(monitor_map, Mapping):
        monitor_map = {}
    max_items = _monitor_items_per_line()

    print("   📡 Monitors :")
    _emit_monitor_lines(monitor_map, max_items=max_items)

    alerts_inline = summary.get("alerts_inline", "pass 0/0 –")
    print(f"   🔔 Alerts   : {alerts_inline}")

    print(f"   {_CYAN}Notifications{_RESET} : {summary.get('notifications_brief', 'NONE (no_breach)')}")

    # Tail
    tail = f"✅ cycle #{cycle_number} done • {total_elapsed:.2f}s  (sleep {poll_interval_s:.1f}s)"
    print(tail, flush=True)
    print("─" * 72)
