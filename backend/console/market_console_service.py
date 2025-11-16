from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from backend.core.core_constants import MOTHER_DB_PATH
from backend.data.data_locker import DataLocker
from backend.core.market_core.market_engine import STATE_OK, evaluate_market_alerts
from backend.models.price_alert import PriceAlert
from backend.models.price_alert_event import PriceAlertEvent


def _make_dl() -> DataLocker:
    # Codex: if you have a helper for building DataLocker with config, use it.
    return DataLocker(str(MOTHER_DB_PATH))


def _load_prices(dl) -> Dict[str, float]:
    rows = dl.prices.select_all()
    prices: Dict[str, float] = {}
    for row in rows:
        sym = row.get("symbol") or row.get("asset") or row.get("ticker")
        if sym is None:
            continue
        prices[str(sym)] = float(row.get("price") or 0.0)
    return prices


# ───────────────────── main menu ─────────────────────


def run_market_console() -> None:
    dl = _make_dl()

    while True:
        print()
        print("╭──────────────────────── Market Core Console ─────────────────────────╮")
        print("│ 1. Market Dashboard (prices + status)                               │")
        print("│ 2. Manage Market Alerts                                             │")
        print("│ 3. Market Activity / XCom History                                   │")
        print("│ 4. Help & Concepts                                                  │")
        print("│ 0. Back to LaunchPad                                                │")
        print("╰──────────────────────────────────────────────────────────────────────╯")
        choice = input("→ ").strip().lower()

        if choice in ("0", "q", "quit", "exit"):
            return
        if choice == "1":
            show_dashboard(dl)
        elif choice == "2":
            manage_alerts(dl)
        elif choice == "3":
            show_history(dl)
        elif choice == "4":
            show_help()


# ───────────────────── dashboard ─────────────────────


def show_dashboard(dl: Any) -> None:
    prices = _load_prices(dl)
    out = evaluate_market_alerts(dl, prices)
    rows: List[Dict[str, Any]] = out["result"]["rows"]

    print()
    print("╭──────────────────────── 📈 Market Dashboard 📈 ──────────────────────╮")
    print("│ Baseline: anchors from Market Core • Data: DL prices                │")
    print("╰──────────────────────────────────────────────────────────────────────╯")
    print()
    print("Asset  Price        Move       Move%    Alert                Proximity  State")

    for r in rows:
        asset = (r.get("asset") or "")[:5]
        price = float(r.get("price") or 0.0)
        move_abs = float(r.get("move_abs") or 0.0)
        move_pct = float(r.get("move_pct") or 0.0)
        threshold_desc = (r.get("threshold_desc") or "")[:20]
        state = r.get("state") or ""
        prox = float(r.get("proximity") or 0.0)
        prox = max(0.0, min(prox, 1.0))
        filled = int(round(prox * 10))
        bar = "▰" * filled + "▱" * (10 - filled)

        print(
            f"{asset:<5} {price:>10.2f} {move_abs:>10.2f} {move_pct:>7.2f}%  "
            f"{threshold_desc:<20} {bar} {state}"
        )

    input("\nPress ENTER to return...")


# ───────────────────── alerts CRUD (minimal) ─────────────────────


def manage_alerts(dl: Any) -> None:
    while True:
        alerts = dl.price_alerts.list_alerts()

        print()
        print("╭──────────────────────── ⚙️ Market Alerts ⚙️ ────────────────────────╮")
        print("│ #  Asset  Type        Dir    Threshold   Recurrence   Enabled       │")
        print("╰──────────────────────────────────────────────────────────────────────╯")
        for idx, a in enumerate(alerts, 1):
            print(
                f"  {idx:<2} {a.asset:<5} {a.rule_type:<11} {a.direction:<6} "
                f"{a.base_threshold_value:>9.2f}   {a.recurrence_mode:<9} {str(a.enabled):<7}"
            )
        print()
        print("A) Add  E) Edit  R) Reset/Re-arm  D) Delete  Q) Back")
        choice = input("→ ").strip().lower()

        if choice in ("0", "q"):
            return
        if choice == "a":
            _ui_add_alert(dl)
        elif choice == "e":
            _ui_edit_alert(dl, alerts)
        elif choice == "d":
            _ui_delete_alert(dl, alerts)
        elif choice == "r":
            _ui_reset_alert(dl, alerts)


def _pick_alert(alerts: List[PriceAlert]) -> PriceAlert | None:
    if not alerts:
        print("No alerts defined.")
        return None
    idx_str = input("Select alert # (ENTER to cancel): ").strip()
    if not idx_str:
        return None
    try:
        idx = int(idx_str)
    except ValueError:
        return None
    if not (1 <= idx <= len(alerts)):
        return None
    return alerts[idx - 1]


def _ui_add_alert(dl: Any) -> None:
    asset = input("Asset (SPX/BTC/ETH/SOL) → ").strip().upper() or "BTC"
    label = input("Label (optional) → ").strip() or None

    print("Type: 1) Move % from anchor  2) Move $ from anchor  3) Price target")
    t = input("→ ").strip()
    if t == "2":
        rule_type = "move_abs"
    elif t == "3":
        rule_type = "price_target"
    else:
        rule_type = "move_pct"

    if rule_type == "price_target":
        print("Direction: 1) above  2) below")
        d = input("→ ").strip()
        direction = "above" if d != "2" else "below"
    else:
        print("Direction: 1) up  2) down  3) both")
        d = input("→ ").strip()
        if d == "1":
            direction = "up"
        elif d == "2":
            direction = "down"
        else:
            direction = "both"

    thr_raw = input("Threshold value → ").strip()
    try:
        thr = float(thr_raw)
    except ValueError:
        thr = 5.0

    print("Recurrence: 1) single  2) reset  3) ladder")
    r = input("→ ").strip()
    if r == "2":
        recurrence = "reset"
    elif r == "3":
        recurrence = "ladder"
    else:
        recurrence = "single"

    alert = PriceAlert(
        asset=asset,
        label=label,
        rule_type=rule_type,
        direction=direction,
        base_threshold_value=thr,
        recurrence_mode=recurrence,
        enabled=True,
    )
    dl.price_alerts.save_alert(alert)
    print("Alert created.")


def _ui_edit_alert(dl: Any, alerts: List[PriceAlert]) -> None:
    alert = _pick_alert(alerts)
    if not alert:
        return

    print(f"Editing alert #{alert.id} ({alert.asset} – {alert.label})")
    new_label = input(f"Label [{alert.label or ''}] → ").strip()
    if new_label:
        alert.label = new_label

    thr_raw = input(f"Threshold [{alert.base_threshold_value}] → ").strip()
    if thr_raw:
        try:
            alert.base_threshold_value = float(thr_raw)
        except ValueError:
            pass

    toggle = input(f"Toggle enabled? currently {alert.enabled} (y/N) → ").strip().lower()
    if toggle == "y":
        alert.enabled = not alert.enabled

    dl.price_alerts.save_alert(alert)
    print("Alert updated.")


def _ui_delete_alert(dl: Any, alerts: List[PriceAlert]) -> None:
    alert = _pick_alert(alerts)
    if not alert:
        return
    confirm = input(f"Delete alert {alert.asset} – {alert.label}? (y/N) → ").strip().lower()
    if confirm == "y" and alert.id is not None:
        dl.price_alerts.delete_alert(alert.id)
        print("Alert deleted.")


def _ui_reset_alert(dl: Any, alerts: List[PriceAlert]) -> None:
    alert = _pick_alert(alerts)
    if not alert:
        return

    print("Reset / Re-arm:")
    print("  1) Re-arm at CURRENT price")
    print("  2) Re-arm at ORIGINAL anchor")
    choice = input("→ ").strip()
    if choice not in ("1", "2"):
        return

    prices = _load_prices(dl)
    current_price = prices.get(alert.asset)
    now_iso = datetime.utcnow().isoformat()  # type: ignore[name-defined]

    if choice == "1" and current_price is not None:
        alert.current_anchor_price = current_price
        alert.current_anchor_time = now_iso
        if alert.original_anchor_price is None:
            alert.original_anchor_price = current_price
            alert.original_anchor_time = now_iso
    else:
        # reset to original anchor
        if alert.original_anchor_price is None:
            print("No original anchor; using current price instead.")
            if current_price is not None:
                alert.original_anchor_price = current_price
                alert.original_anchor_time = now_iso
                alert.current_anchor_price = current_price
                alert.current_anchor_time = now_iso
        else:
            alert.current_anchor_price = alert.original_anchor_price
            alert.current_anchor_time = alert.original_anchor_time or now_iso

    alert.armed = True
    alert.last_reset_at = now_iso
    alert.last_state = STATE_OK
    alert.updated_at = now_iso
    dl.price_alerts.save_alert(alert)
    print("Alert re-armed.")


# ───────────────────── history ─────────────────────


def show_history(dl: Any) -> None:
    events: List[PriceAlertEvent] = dl.price_alert_events.get_recent(limit=50)
    print()
    print("╭──────────── 🛰 Market Activity / XCom History ────────────╮")
    print("│ Time (UTC)           Asset  Type      State   Price  Move% │")
    print("╰────────────────────────────────────────────────────────────╯")

    for ev in events:
        t = ev.created_at
        try:
            dt = datetime.fromisoformat(str(t))
            t_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            t_str = str(t)
        move_pct = ev.movement_percent or 0.0
        print(
            f"{t_str}  {ev.asset:<5} {ev.event_type:<9} "
            f"{(ev.state_after or ''):<6} {(ev.price_at_event or 0.0):>8.2f} {move_pct:>7.2f}%"
        )

    input("\nPress ENTER to return...")


# ───────────────────── help ─────────────────────


def show_help() -> None:
    print()
    print("╭────────────────────── Help & Concepts ───────────────────────╮")
    print("│ • Anchor: remembered price used as baseline for movement     │")
    print("│   alerts. 'Move 5% from anchor' compares current vs anchor.  │")
    print("│                                                              │")
    print("│ • Threshold: how big a move you care about.                  │")
    print("│   – Percent move  (≥ X% from anchor)                         │")
    print("│   – Dollar move   (≥ $X from anchor)                         │")
    print("│   – Target price  (crosses a fixed level)                    │")
    print("│                                                              │")
    print("│ • Recurrence: what happens after an alert fires:             │")
    print("│   – single : alert once, then disarmed until reset           │")
    print("│   – reset  : alert, then anchor jumps to the new price       │")
    print("│   – ladder : alert on each step of size threshold            │")
    print("│                                                              │")
    print("│ • Reset: you can re-arm an alert at the current price or     │")
    print("│   the original anchor, restarting distance to threshold.     │")
    print("│                                                              │")
    print("│ • Proximity bar: shows how close the current move is to the  │")
    print("│   threshold. 0% = empty, 100% = alert fires.                 │")
    print("╰──────────────────────────────────────────────────────────────╯")
    input("\nPress ENTER to return...")


if __name__ == "__main__":
    run_market_console()
