import datetime
from typing import Dict, Any, List, Tuple, Optional

_GREEN = "\x1b[32m"
_YELLOW = "\x1b[33m"
_RED = "\x1b[31m"
_DIM = "\x1b[90m"
_RESET = "\x1b[0m"

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
        label = symbol
        if enable_color:
            age = (ages or {}).get(symbol, 999_999)
            if age == 0:
                label = f"{_GREEN}{symbol}{_RESET}"
            elif 2 <= age <= 5:
                label = f"{_YELLOW}{symbol}{_RESET}"
            elif age > 5:
                label = f"{_RED}{symbol}{_RESET}"
        parts.append(f"{label}=${price:,.2f}")
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
    elapsed_seconds = f"{float(summary.get('elapsed_s') or 0.0):.0f}"
    cycle_number = summary.get("cycle_num", "?")

    # Cyclone headline
    line = (
        "   🌀 Cyclone  : "
        f"{summary.get('positions_line', '↑0/0/0')} • {summary.get('hedge_groups', 0)} hedges • {elapsed_seconds} seconds"
    )
    print(line, flush=True)

    # Prices
    prices_when = _fmt_short_clock(summary.get("prices_updated_at"))
    print(
        "   💰 Prices   : "
        f"{_prices_line(summary.get('prices_top3', []), summary.get('price_ages', {}), enable_color=enable_color)}  • @ {prices_when}"
    )

    # Positions
    pos_line = summary.get("positions_line", "↑0/0/0")
    pos_when = _fmt_short_clock(summary.get("positions_updated_at"))
    pos_error = summary.get("positions_error")
    if pos_error:
        print(f"   📊 Positions: {pos_line}  • @ {pos_when} — {_RED}{pos_error}{_RESET}")
    else:
        print(f"   📊 Positions: {pos_line}  • @ {pos_when}")

    # Holdings brief
    brief = summary.get("positions_brief", "–")
    print(f"   📄 Holdings : {brief}")

    # Hedges
    print(f"   🛡  Hedges  : {'🦔' if int(summary.get('hedge_groups', 0) or 0) > 0 else '–'}")

    # Alerts (cheap inline)
    alerts_inline = summary.get("alerts_inline", "pass 0/0 –")
    print(f"   🔔 Alerts   : {alerts_inline}")

    # Optional notifications line (kept from your previous build)
    notif = summary.get("notifications_brief", "NONE (no_breach)")
    print(f"\n   📨 Notifications : {notif}")

    # Tail
    total_elapsed = float(summary.get("elapsed_s") or 0.0)
    tail = f"✅ cycle #{cycle_number} done • {total_elapsed:.2f}s  (sleep {poll_interval_s:.1f}s)"
    print(tail, flush=True)
