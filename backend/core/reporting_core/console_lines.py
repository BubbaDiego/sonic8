import datetime
from typing import Dict, Any, List, Tuple, Optional

_GREEN = "\x1b[32m"
_YELLOW = "\x1b[33m"
_RED = "\x1b[31m"
_DIM = "\x1b[90m"
_RESET = "\x1b[0m"

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
    total_elapsed = float(summary.get("elapsed_s") or 0.0)
    cycle_number = summary.get("cycle_num", "?")

    # 🌀 Cyclone headline (simplified status icon + elapsed seconds)
    errs = int(summary.get("errors_count", 0) or 0)
    mons = summary.get("monitors_inline") or ""
    al_inline = summary.get("alerts_inline") or ""
    has_fail = (errs > 0) or ("FAIL" in mons)
    has_alert = ("breach" in str(al_inline).lower()) or ("ALERT" in str(al_inline))
    icon = "☠️" if has_fail else ("⚠️" if has_alert else "✅")
    line = f"   🌀 Cyclone  : {icon} {int(max(total_elapsed, 0.0))}s"
    print(line, flush=True)

    # Prices
    prices_top3 = summary.get("prices_top3", [])
    prices_when = _fmt_short_clock(summary.get("prices_updated_at"))
    prices_reason = summary.get("prices_reason")
    price_prefix = f"({prices_reason}) " if prices_reason else ""
    if prices_top3:
        line = _prices_line(prices_top3, summary.get("price_ages", {}), enable_color=enable_color)
        print(f"   💰 Prices   : {price_prefix}{line}  • @ {prices_when}")
    else:
        print(f"   💰 Prices   : {price_prefix}–  • @ –")

    # Positions
    pos_line = summary.get("positions_icon_line")
    pos_when = _fmt_short_clock(summary.get("positions_updated_at"))
    pos_reason = summary.get("positions_reason")
    pos_prefix = f"({pos_reason}) " if pos_reason else ""
    if pos_line:
        print(f"   📊 Positions: {pos_prefix}{pos_line}  • @ {pos_when}")
    else:
        print(f"   📊 Positions: {pos_prefix}–  • @ –")

    # Hedges — render one hedgehog per active hedge group
    hedge_count = int(summary.get("hedge_groups", 0) or 0)
    hedgehogs = "".join("🦔" for _ in range(hedge_count)) if hedge_count > 0 else "–"
    print(f"   🛡  Hedges  : {hedgehogs}")

    # Alerts (cheap inline)
    alerts_inline = summary.get("alerts_inline", "pass 0/0 –")
    print(f"   🔔 Alerts   : {alerts_inline}")

    # Monitors inline (optional)
    mon_inline = summary.get("monitors_inline")
    if mon_inline:
        print(f"   📡 Monitors : {mon_inline}")

    # Optional notifications line (kept from your previous build)
    notif = summary.get("notifications_brief", "NONE (no_breach)")
    print(f"   📨 Notifications : {notif}")
    print()

    # Tail
    tail = f"✅ cycle #{cycle_number} done • {total_elapsed:.2f}s  (sleep {poll_interval_s:.1f}s)"
    print(tail, flush=True)
    print("─" * 72)
