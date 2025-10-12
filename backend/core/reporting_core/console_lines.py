import datetime
import logging
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

def emit_compact_cycle(
    csum: Dict[str, Any],
    loop_counter: int,
    total_elapsed: float,
    sleep_time: float,
) -> None:
    """
    Sonic6-compatible compact cycle summary.
    The snapshot is expected to look like Cyclone.get_summary_snapshot(), but the
    function defensively tolerates missing keys or unexpected types.
    """

    def _as_dict(val: Any) -> Dict[str, Any]:
        return val if isinstance(val, dict) else {}

    prices = _as_dict(csum.get("prices"))
    positions = _as_dict(csum.get("positions"))
    hedges = _as_dict(csum.get("hedges"))
    alerts = _as_dict(csum.get("alerts"))
    monitors = _as_dict(csum.get("monitors"))

    cycle_ms = int(max(total_elapsed * 1000.0, 1))

    # 🌀 Cyclone headline
    headline = (
        "   🌀 Cyclone  : "
        f"{prices.get('assets_line', '–')} • "
        f"{positions.get('sync_line', '–')} • "
        f"{alerts.get('line', '–')} • "
        f"groups {hedges.get('groups', 0)} • {cycle_ms}ms"
    )
    print(headline, flush=True)

    # 💰 Prices
    if prices:
        assets_cnt = prices.get("assets", 0)
        price_line = f"   💰 Prices   : ✓ assets={assets_cnt}"
        errors = prices.get("errors")
        if errors:
            price_line += f" • {errors}"
        print(price_line, flush=True)

    # 📊 Positions
    if positions:
        enrich = positions.get("enrich", 0)
        print(
            "   📊 Positions: "
            f"{positions.get('sync_line', '–')} • enrich {enrich}",
            flush=True,
        )

    # 🛡 Hedges (only when groups > 0)
    hedge_groups = hedges.get("groups", 0)
    if hedge_groups:
        print(f"   🛡 Hedges   : groups {hedge_groups}", flush=True)

    # 🔔 Alerts
    if alerts:
        print(f"   🔔 Alerts   : {alerts.get('line', '–')}", flush=True)

    # 📡 Monitors
    if monitors:
        try:
            tokens = " ".join(f"{k}:{v}" for k, v in monitors.items())
        except Exception:
            logging.debug("Unable to render monitor tokens: %r", monitors)
            tokens = ""
        if tokens:
            print(f"   📡 Monitors : {tokens}", flush=True)

    tail = f"✅ cycle #{loop_counter} done • {total_elapsed:.2f}s  (sleep {sleep_time:.1f}s)"
    print(tail, flush=True)
