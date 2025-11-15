# -*- coding: utf-8 -*-
"""
Market Core Console

Text UI to:
  • view latest market prices + alert proximity
  • manage price alerts
  • inspect recent alert/XCom history
  • read help on anchors / recurrence

Wire this into LaunchPad as "📈 Market Console" with hotkey 'M'.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List, Optional

from backend.data.data_locker import DataLocker
from backend.models.price_alert import (
    PriceAlert,
    PriceAlertMode,
    PriceAlertDirection,
    PriceAlertRecurrence,
    PriceAlertConfig,
)
from backend.models.price_alert_event import PriceAlertEvent
from backend.core.market_core.market_core import MarketCore


# ───────────────────────── helpers ─────────────────────────

def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _pause(msg: str = "Press ENTER to continue…") -> None:
    try:
        input(msg)
    except EOFError:
        pass


def _get_prices(dl: DataLocker) -> Dict[str, float]:
    """
    Fetch latest prices for SPX, BTC, ETH, SOL from the DLPriceManager when available.

    The DL implementation stores the field as ``current_price``. This helper silently
    ignores symbols that are missing.
    """

    prices: Dict[str, float] = {}
    manager = getattr(dl, "prices", None)
    if manager is None:
        return prices

    for symbol in ("SPX", "BTC", "ETH", "SOL"):
        try:
            row = manager.get_latest_price(symbol)
        except Exception:
            row = None
        if not row:
            continue
        value = row.get("current_price") or row.get("price")
        if value is None:
            continue
        try:
            prices[symbol] = float(value)
        except (TypeError, ValueError):
            continue
    return prices


# ───────────────────────── UI: main menu ────────────────────

def run_console(dl: DataLocker) -> None:
    while True:
        _clear()
        print("╭──────────────────────── Market Core Console ────────────────────────╮")
        print("│                                                                      │")
        print("│  1. Market Dashboard (prices + proximity)                            │")
        print("│  2. Manage Alerts (add / edit / delete / reset)                     │")
        print("│  3. Event History                                                    │")
        print("│  4. Help & Concepts                                                  │")
        print("│                                                                      │")
        print("│  0. Back to LaunchPad                                                │")
        print("│                                                                      │")
        print("╰──────────────────────────────────────────────────────────────────────╯")
        choice = input("→ ").strip().lower()

        if choice == "1":
            show_dashboard(dl)
        elif choice == "2":
            manage_alerts(dl)
        elif choice == "3":
            show_history(dl)
        elif choice == "4":
            show_help()
        elif choice in ("0", "q"):
            break


# ───────────────────────── UI: dashboard ─────────────────────

def show_dashboard(dl: DataLocker) -> None:
    _clear()
    alerts = dl.price_alerts.list_alerts()
    prices = _get_prices(dl)

    core = MarketCore(alerts, prices)
    result = core.evaluate()

    # Persist updated alerts (anchors, states)
    for a in result.alerts:
        dl.price_alerts.save_alert(a)
    # Record events
    for e in result.events:
        dl.price_alert_events.record_event(e, ensure_schema_first=True)

    print("╭──────────────────────── 📈 Market Dashboard 📈 ──────────────────────╮")
    print("│  Asset  Price        Move       Move%     Threshold      Proximity  │")
    print("╰──────────────────────────────────────────────────────────────────────╯")

    for status in result.statuses:
        price = status.price if status.price is not None else 0.0
        move_abs = status.move_abs if status.move_abs is not None else 0.0
        move_pct = status.move_pct if status.move_pct is not None else 0.0
        prox = min(max(status.proximity_ratio, 0.0), 1.0)
        bar_len = 10
        filled = int(round(prox * bar_len))
        bar = "▰" * filled + "▱" * (bar_len - filled)

        print(
            f"{status.asset:<5} "
            f"{price:>10.2f}  "
            f"{move_abs:>8.2f}  "
            f"{move_pct:>7.2f}%  "
            f"{status.threshold_value:>10.2f}  "
            f"{bar} {status.state.value}"
        )

    print()
    _pause()


# ───────────────────────── UI: manage alerts ─────────────────

def manage_alerts(dl: DataLocker) -> None:
    while True:
        _clear()
        alerts = dl.price_alerts.list_alerts()
        print("╭──────────────────────── ⚙️ Market Alerts ⚙️ ────────────────────────╮")
        print("│ #  Asset  Mode         Dir    Threshold   Recurrence   Enabled      │")
        print("╰──────────────────────────────────────────────────────────────────────╯")
        for idx, a in enumerate(alerts, start=1):
            cfg = a.config
            print(
                f"{idx:<2} "
                f"{cfg.asset:<5} "
                f"{cfg.mode.value:<11} "
                f"{cfg.direction.value:<6} "
                f"{cfg.threshold_value:>9.2f}   "
                f"{cfg.recurrence.value:<10} "
                f"{'ON ' if cfg.enabled else 'OFF'}"
            )
        print()
        print("[A]dd  [E]dit  [D]elete  [R]eset/Re-arm  [Q] back")
        choice = input("→ ").strip().lower()

        if choice == "a":
            create_alert(dl)
        elif choice == "e":
            edit_alert(dl, alerts)
        elif choice == "d":
            delete_alert(dl, alerts)
        elif choice == "r":
            reset_alert(dl, alerts)
        elif choice in ("q", "0"):
            break


def _select_alert(alerts: List[PriceAlert]) -> Optional[PriceAlert]:
    if not alerts:
        _pause("No alerts defined yet. Press ENTER…")
        return None
    idx_str = input("Select alert # → ").strip()
    if not idx_str.isdigit():
        return None
    idx = int(idx_str)
    if 1 <= idx <= len(alerts):
        return alerts[idx - 1]
    return None


def create_alert(dl: DataLocker) -> None:
    print("Create new alert")
    asset = input("Asset (SPX/BTC/ETH/SOL) → ").strip().upper() or "BTC"

    print("Mode:")
    print("  1) move_percent  (percent move from anchor)")
    print("  2) move_absolute (dollar move from anchor)")
    print("  3) price_target  (crosses a fixed price)")
    mode_choice = input("→ ").strip() or "1"
    mode = {
        "1": PriceAlertMode.MOVE_PERCENT,
        "2": PriceAlertMode.MOVE_ABSOLUTE,
        "3": PriceAlertMode.PRICE_TARGET,
    }.get(mode_choice, PriceAlertMode.MOVE_PERCENT)

    if mode == PriceAlertMode.PRICE_TARGET:
        print("Direction:")
        print("  1) above (price >= target)")
        print("  2) below (price <= target)")
        d_choice = input("→ ").strip() or "1"
        direction = (
            PriceAlertDirection.ABOVE
            if d_choice == "1"
            else PriceAlertDirection.BELOW
        )
    else:
        print("Direction:")
        print("  1) up")
        print("  2) down")
        print("  3) both")
        d_choice = input("→ ").strip() or "3"
        direction = {
            "1": PriceAlertDirection.UP,
            "2": PriceAlertDirection.DOWN,
            "3": PriceAlertDirection.BOTH,
        }.get(d_choice, PriceAlertDirection.BOTH)

    thr_raw = input("Threshold value → ").strip()
    try:
        thr = float(thr_raw)
    except Exception:
        thr = 5.0

    print("Recurrence:")
    print("  1) single (fire once, then disarm)")
    print("  2) reset  (fire, then anchor jumps to current price)")
    print("  3) ladder (stepwise trend tracking)")
    r_choice = input("→ ").strip() or "1"
    recurrence = {
        "1": PriceAlertRecurrence.SINGLE,
        "2": PriceAlertRecurrence.RESET,
        "3": PriceAlertRecurrence.LADDER,
    }.get(r_choice, PriceAlertRecurrence.SINGLE)

    name = input("Label (optional) → ").strip() or None

    cfg = PriceAlertConfig(
        id=None,
        asset=asset,
        name=name,
        enabled=True,
        mode=mode,
        direction=direction,
        threshold_value=thr,
        original_threshold_value=thr,
        recurrence=recurrence,
        cooldown_seconds=0,
    )
    alert = PriceAlert(config=cfg)
    dl.price_alerts.save_alert(alert)
    _pause("Alert created. Press ENTER…")


def edit_alert(dl: DataLocker, alerts: List[PriceAlert]) -> None:
    sel = _select_alert(alerts)
    if not sel:
        return
    cfg = sel.config

    print(f"Editing alert id={cfg.id} ({cfg.asset})")
    name = input(f"Label [{cfg.name or ''}] → ").strip() or cfg.name
    thr_raw = input(f"Threshold [{cfg.threshold_value}] → ").strip()
    thr = cfg.threshold_value
    if thr_raw:
        try:
            thr = float(thr_raw)
        except Exception:
            pass

    cfg = cfg.copy(
        update={
            "name": name,
            "threshold_value": thr,
        }
    )
    alert = PriceAlert(config=cfg, state=sel.state)
    dl.price_alerts.save_alert(alert)
    _pause("Alert updated. Press ENTER…")


def delete_alert(dl: DataLocker, alerts: List[PriceAlert]) -> None:
    sel = _select_alert(alerts)
    if not sel:
        return
    cfg = sel.config
    confirm = input(f"Delete alert id={cfg.id} ({cfg.asset})? [y/N] → ").strip().lower()
    if confirm == "y":
        if cfg.id is not None:
            dl.price_alerts.delete_alert(cfg.id)
        _pause("Alert deleted. Press ENTER…")


def reset_alert(dl: DataLocker, alerts: List[PriceAlert]) -> None:
    sel = _select_alert(alerts)
    if not sel:
        return
    cfg = sel.config
    st = sel.state

    print(f"Reset / Re-arm alert id={cfg.id} ({cfg.asset})")
    print("  1) Re-arm at CURRENT price (anchor = latest price)")
    print("  2) Re-arm at ORIGINAL anchor (anchor = original_anchor_price)")
    print("  0) Cancel")
    choice = input("→ ").strip() or "0"
    if choice not in ("1", "2"):
        return

    now = datetime.utcnow()
    prices = _get_prices(dl)
    price = prices.get(cfg.asset)

    if choice == "1" and price is not None:
        new_state = st.copy(
            update={
                "current_anchor_price": price,
                "current_anchor_time": now,
                "armed": True,
                "last_reset_at": now,
            }
        )
    else:
        new_state = st.copy(
            update={
                "current_anchor_price": st.original_anchor_price,
                "current_anchor_time": st.original_anchor_time or now,
                "armed": True,
                "last_reset_at": now,
            }
        )

    alert = PriceAlert(config=cfg, state=new_state)
    dl.price_alerts.save_alert(alert)
    _pause("Alert re-armed. Press ENTER…")


# ───────────────────────── UI: history ──────────────────────

def show_history(dl: DataLocker) -> None:
    _clear()
    events: List[PriceAlertEvent] = dl.price_alert_events.get_recent(limit=50)
    print("╭──────────────────── 🛰 Market Alert History ───────────────────────╮")
    print("│  Time (UTC)           Asset  Type      State   Price      Move%    │")
    print("╰────────────────────────────────────────────────────────────────────╯")
    for e in events:
        t = e.created_at if isinstance(e.created_at, datetime) else datetime.fromisoformat(str(e.created_at))
        move_pct = e.movement_pct if e.movement_pct is not None else 0.0
        price = e.price if e.price is not None else 0.0
        print(
            f"{t:%Y-%m-%d %H:%M:%S}  "
            f"{(e.asset or '?'):<5}  "
            f"{e.event_type.value:<9} "
            f"{e.state_after.value:<6} "
            f"{price:>9.2f}  "
            f"{move_pct:>7.2f}%"
        )
    print()
    _pause()


# ───────────────────────── UI: help ─────────────────────────

def show_help() -> None:
    _clear()
    print("╭────────────────────── Help & Concepts ───────────────────────╮")
    print("│                                                              │")
    print("│ • Anchor: a remembered price used as the baseline for        │")
    print("│   movement alerts. 'Move 5% from anchor' compares the        │")
    print("│   current price to this anchor.                              │")
    print("│                                                              │")
    print("│ • Threshold: how big a move you care about.                  │")
    print("│   – Percent move  (≥ X% from anchor)                        │")
    print("│   – Dollar move   (≥ $X from anchor)                         │")
    print("│   – Target price  (crosses a fixed level)                    │")
    print("│                                                              │")
    print("│ • Recurrence: what happens after an alert fires:             │")
    print("│   – single : alert once, then disarmed until reset           │")
    print("│   – reset  : alert, then anchor jumps to the new price       │")
    print("│   – ladder : alert on each step of size threshold            │")
    print("│                                                              │")
    print("│ • Reset: you can re-arm an alert at the current price or     │")
    print("│   the original anchor, restarting the distance to threshold. │")
    print("│                                                              │")
    print("│ • Proximity bar: shows how close the current move is to      │")
    print("│   the threshold. 0% = empty, 100% = alert fires.             │")
    print("│                                                              │")
    print("╰──────────────────────────────────────────────────────────────╯")
    _pause()


# ───────────────────────── entrypoint ────────────────────────

def main() -> None:
    """
    Entry point when run as a script.

    Uses the DataLocker singleton to reuse the primary database connection.
    """

    try:
        dl = DataLocker.get_instance()  # type: ignore[attr-defined]
    except Exception:
        from backend.core.core_constants import MOTHER_DB_PATH

        dl = DataLocker(str(MOTHER_DB_PATH))
    run_console(dl)


if __name__ == "__main__":
    main()
