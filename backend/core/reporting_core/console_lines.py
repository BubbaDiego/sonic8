import datetime
from typing import Dict, Any, List, Tuple, Optional

_GREEN = "\x1b[32m"
_YELLOW = "\x1b[33m"
_RED = "\x1b[31m"
_RESET = "\x1b[0m"

def _fmt_short_clock(iso: Optional[str]) -> str:
    if not iso:
        return "–"
    try:
        if iso.endswith("Z"):
            dt = datetime.datetime.fromisoformat(iso[:-1] + "+00:00")
        else:
            dt = datetime.datetime.fromisoformat(iso)
        return dt.strftime("%H:%M:%S")
    except Exception:
        return "–"

def _prices_line(
    top3: List[Tuple[str, float]],
    ages: Optional[Dict[str, int]] = None,
    *,
    enable_color: bool = False,
    changes: Optional[Dict[str, bool]] = None,
) -> str:
    if not top3:
        return "–"
    parts: List[str] = []
    for symbol, price in top3:
        label = symbol
        if enable_color:
            age = (ages or {}).get(symbol, 999_999)
            changed = (changes or {}).get(symbol, False)
            if age == 0:
                # highlight only if price actually changed at this tick
                label = f"{_GREEN}{symbol}{_RESET}" if changed else symbol
            elif 2 <= age <= 5:
                label = f"{_YELLOW}{symbol}{_RESET}"
            elif age > 5:
                label = f"{_RED}{symbol}{_RESET}"
        parts.append(f"{label}=${price:,.2f}")
    return "  ".join(parts)

def emit_compact_cycle(summary: Dict[str, Any], cfg: Dict[str, Any], poll_interval_s: int, *, enable_color: bool = True) -> None:
    # Cyclone headline
    cyc_ms = int(max((summary.get("elapsed_s") or 0.0) * 1000.0, 1))
    pos_line = summary.get("positions_line", "↑0/0/0")
    hedges = int(summary.get("hedge_groups", 0) or 0)
    alerts = summary.get("alerts_inline", "pass 0/0 –")
    line = (
        "   🌀 Cyclone  : "
        f"{summary.get('assets_line','–')} • {pos_line} • {alerts} • groups {hedges} • {cyc_ms}ms"
    )
    print(line, flush=True)

    # Prices
    prices_when = _fmt_short_clock(summary.get("prices_updated_at"))
    print(
        "   💰 Prices   : "
        f"{_prices_line(summary.get('prices_top3', []), summary.get('price_ages', {}), enable_color=enable_color, changes=summary.get('price_changes', {}))}  • @ {prices_when}"
    )

    # Positions
    pos_when = _fmt_short_clock(summary.get("positions_updated_at"))
    print(f"   📊 Positions: {pos_line}  • @ {pos_when}")

    # Holdings
    brief = summary.get("positions_brief", "–")
    print(f"   📄 Holdings : {brief}")

    # Hedges
    print(f"   🛡  Hedges  : {(''.join('🦔' for _ in range(hedges))) if hedges > 0 else '–'}")

    # Alerts + Notifications
    print(f"   🔔 Alerts   : {alerts}")
    print(f"\n   📨 Notifications : {summary.get('notifications_brief', 'NONE (no_breach)')}")

    # Tail
    total_elapsed = float(summary.get("elapsed_s") or 0.0)
    tail = f"✅ cycle #{int(summary.get('cycle_num') or 0)} done • {total_elapsed:.2f}s  (sleep {poll_interval_s:.1f}s)"
    print(tail, flush=True)
