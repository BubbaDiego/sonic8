from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from backend.core.core_constants import MOTHER_DB_PATH
from backend.data.data_locker import DataLocker
from backend.core.market_core.market_engine import evaluate_market_alerts
from backend.models.price_alert import PriceAlert
from backend.models.price_alert_event import PriceAlertEvent


def _make_dl() -> DataLocker:
    # Codex: if you have a helper for building DataLocker with config, use it.
    return DataLocker(str(MOTHER_DB_PATH))


def _load_prices(dl) -> Dict[str, float]:
    """Fetch latest prices for key assets using DLPriceManager."""

    prices: Dict[str, float] = {}
    mgr = getattr(dl, "prices", None)
    if mgr is None:
        return prices

    rows = None
    for method_name in ("get_all_prices", "select_all", "list_all"):
        method = getattr(mgr, method_name, None)
        if not callable(method):
            continue
        try:
            rows = method()
            break
        except Exception:
            rows = None

    if not rows:
        return prices

    tracked_assets = {"SPX", "BTC", "ETH", "SOL", "^GSPC", "SP500"}

    for row in rows:
        if isinstance(row, dict):
            sym = (
                row.get("asset_type")
                or row.get("symbol")
                or row.get("asset")
                or row.get("ticker")
            )
            price = row.get("current_price") or row.get("price")
        else:
            sym = (
                getattr(row, "asset_type", None)
                or getattr(row, "symbol", None)
                or getattr(row, "asset", None)
            )
            price = getattr(row, "current_price", None) or getattr(row, "price", None)

        if sym is None or price is None:
            continue

        sym_str = str(sym).upper()
        if sym_str not in tracked_assets:
            continue

        if sym_str in ("^GSPC", "SP500"):
            sym_str = "SPX"

        # rows are NEWEST → OLDEST; first win per symbol
        if sym_str in prices:
            continue

        try:
            prices[sym_str] = float(price)
        except (TypeError, ValueError):
            continue

    return prices


# ───────────────────── main menu ─────────────────────


def run_market_console() -> None:
    dl = _make_dl()

    while True:
        print()
        print("╭──────────────────────── 📊 Market Core Console ─────────────────────────╮")
        print("│                                                                          │")
        print("│  1. 📈 Market Dashboard      – live prices & alert proximity             │")
        print("│  2. ⚙️  Manage Alerts         – add / edit / reset / delete              │")
        print("│  3. 🛰️  Activity / XCom Log   – recent breaches & history                │")
        print("│  4. 📖 Help & Concepts        – anchors, thresholds, recurrence          │")
        print("│                                                                          │")
        print("│  0. ⏪ Back to LaunchPad                                                  │")
        print("│                                                                          │")
        print("╰──────────────────────────────────────────────────────────────────────────╯")
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
    print("│ Baseline: 🎯 anchors from Market Core • Data: 💾 DL prices           │")
    print("╰──────────────────────────────────────────────────────────────────────╯")
    print()
    print(
        "   🪙Asset    💵Price      📉Move      📊Move%    🎯 Alert           🔋 Proximity  🧾 State"
    )
    print("   ────────────────────────────────────────────────────────────────────────────────")

    if not rows:
        print("   (no alerts yet – add some in ⚙️  Manage Alerts)")
    else:
        for r in rows:
            asset = (r.get("asset") or "")[:5]
            price = float(r.get("price") or 0.0)
            move_abs = float(r.get("move_abs") or 0.0)
            move_pct = float(r.get("move_pct") or 0.0)
            threshold_desc = (r.get("threshold_desc") or "")[:18]
            state = r.get("state") or ""
            prox = float(r.get("proximity") or 0.0)
            prox = max(0.0, min(prox, 1.0))
            filled = int(round(prox * 10))
            bar = "▰" * filled + "▱" * (10 - filled)

            print(
                f"   {asset:<5}  {price:>9.2f}  {move_abs:>9.2f}  "
                f"{move_pct:>7.2f}%   {threshold_desc:<18}  {bar}  {state:<7}"
            )

    input("\n⏎  Press ENTER to return...")


# ───────────────────── alerts CRUD (minimal) ─────────────────────


def manage_alerts(dl: Any) -> None:
    while True:
        alerts = dl.price_alerts.list_alerts()

        print()
        print("╭──────────────────────── ⚙️ Market Alerts ⚙️ ────────────────────────╮")
        print("│ #  🪙Asset  📐Type       ↕ Dir   🎯Thresh    🔁 Recurrence   ✅ Enabled │")
        print("╰──────────────────────────────────────────────────────────────────────╯")
        for idx, a in enumerate(alerts, 1):
            print(
                f"  {idx:<2} {a.asset:<5} {a.rule_type:<11} {a.direction:<6} "
                f"{a.base_threshold_value:>9.2f}   {a.recurrence_mode:<10} "
                f"{'ON ' if a.enabled else 'OFF'}"
            )
        print()
        print("  1) 🆕  Add alert")
        print("  2) ✏️  Edit alert")
        print("  3) 🔁  Reset/Re-arm alert")
        print("  4) 🗑  Delete alert")
        print("  5) 💣  Delete ALL alerts")
        print("  0) ⏪  Back")
        choice = input("→ ").strip().lower()

        if choice in ("0", "q"):
            return
        if choice in ("1", "a"):
            _ui_add_alert(dl)
        elif choice in ("2", "e"):
            _ui_edit_alert(dl, alerts)
        elif choice in ("3", "r"):
            _ui_reset_alert(dl, alerts)
        elif choice in ("4", "d"):
            _ui_delete_alert(dl, alerts)
        elif choice in ("5", "x"):
            _ui_delete_all_alerts(dl, alerts)


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
    # --- Asset selection ---
    print()
    print("Choose asset:")
    assets = ["SPX", "BTC", "ETH", "SOL"]
    for i, sym in enumerate(assets, 1):
        print(f"  {i}) {sym}")
    while True:
        choice = input("→ ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(assets):
            asset = assets[int(choice) - 1]
            break
        print("  Invalid selection. Please enter 1–4.")

    label = input("Label (optional) → ").strip() or None

    # --- Type selection ---
    print()
    print("Alert type:")
    print("  1) Move % from anchor")
    print("  2) Move $ from anchor")
    print("  3) Price target")
    while True:
        t = input("→ ").strip()
        if t == "2":
            rule_type = "move_abs"
            break
        elif t == "3":
            rule_type = "price_target"
            break
        elif t == "1" or t == "":
            rule_type = "move_pct"
            break
        print("  Invalid selection. Please enter 1, 2, or 3.")

    # --- Direction selection ---
    print()
    if rule_type == "price_target":
        print("Direction (price target):")
        print("  1) above  (price ≥ target)")
        print("  2) below  (price ≤ target)")
        while True:
            d = input("→ ").strip()
            if d in ("1", "2", ""):
                direction = "above" if d != "2" else "below"
                break
            print("  Invalid selection. Please enter 1 or 2.")
    else:
        print("Direction (movement):")
        print("  1) up")
        print("  2) down")
        print("  3) both")
        while True:
            d = input("→ ").strip()
            if d == "1":
                direction = "up"
                break
            elif d == "2":
                direction = "down"
                break
            elif d in ("3", ""):
                direction = "both"
                break
            print("  Invalid selection. Please enter 1, 2, or 3.")

    # --- Threshold value ---
    print()
    if rule_type == "move_pct":
        prompt = "Threshold value (percent, e.g. 5 for 5%) → "
    elif rule_type == "move_abs":
        prompt = "Threshold value ($ move from anchor, e.g. 100) → "
    else:
        prompt = "Target price (e.g. 4200.00) → "
    thr_raw = input(prompt).strip()
    try:
        base_threshold_value = float(thr_raw)
    except ValueError:
        base_threshold_value = 5.0

    # --- Recurrence selection ---
    print()
    print("Recurrence:")
    print("  1) single  – alert once, then disarm")
    print("  2) reset   – alert, then anchor jumps to current price")
    print("  3) ladder  – alert on each step of size threshold")
    while True:
        r = input("→ ").strip()
        if r in ("1", ""):
            recurrence_mode = "single"
            break
        elif r == "2":
            recurrence_mode = "reset"
            break
        elif r == "3":
            recurrence_mode = "ladder"
            break
        print("  Invalid selection. Please enter 1, 2, or 3.")

    # --- Build and save the alert ---
    alert = PriceAlert(
        asset=asset,
        label=label,
        rule_type=rule_type,
        direction=direction,
        base_threshold_value=base_threshold_value,
        recurrence_mode=recurrence_mode,
        enabled=True,
    )
    dl.price_alerts.save_alert(alert)
    print("\n✅ Alert created.")
    input("⏎  Press ENTER to return...")


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


def _ui_delete_all_alerts(dl: Any, alerts: List[PriceAlert]) -> None:
    """Delete all market alerts with a confirmation that defaults to YES."""
    if not alerts:
        print("No alerts defined.")
        input("⏎  Press ENTER to continue...")
        return

    print()
    print("💣 Delete ALL alerts")
    print("---------------------")
    confirm = input("Delete ALL alerts? [Y/n] → ").strip().lower()

    # Default to YES: blank or 'y'/'yes' proceed; anything else cancels.
    if confirm not in ("", "y", "yes"):
        print("Aborted. No alerts were deleted.")
        input("⏎  Press ENTER to continue...")
        return

    deleted = 0
    for alert in alerts:
        if alert.id is not None:
            dl.price_alerts.delete_alert(alert.id)
            deleted += 1

    print(f"Deleted {deleted} alert(s).")
    input("⏎  Press ENTER to continue...")


def _ui_reset_alert(dl: Any, alerts: List[PriceAlert]) -> None:
    alert = _pick_alert(alerts)
    if not alert:
        return

    print(f"Reset / Re-arm: {alert.asset} – {alert.label or ''}")
    print("  1) Re-arm at CURRENT price")
    print("  2) Re-arm at ORIGINAL anchor")
    choice = input("→ ").strip()
    if choice not in ("1", "2"):
        return

    prices = _load_prices(dl)
    current_price = prices.get(alert.asset)
    now_iso = datetime.utcnow().isoformat()

    if choice == "1" and current_price is not None:
        alert.current_anchor_price = current_price
        alert.current_anchor_time = now_iso
        if alert.original_anchor_price is None:
            alert.original_anchor_price = current_price
            alert.original_anchor_time = now_iso
    else:
        # reset to original anchor (fallback to current if none)
        if alert.original_anchor_price is None and current_price is not None:
            alert.original_anchor_price = current_price
            alert.original_anchor_time = now_iso
        alert.current_anchor_price = alert.original_anchor_price
        alert.current_anchor_time = alert.original_anchor_time or now_iso

    alert.armed = True
    alert.last_reset_at = now_iso
    alert.last_state = "OK"
    alert.updated_at = now_iso
    dl.price_alerts.save_alert(alert)
    print("Alert re-armed.")


# ───────────────────── history ─────────────────────


def show_history(dl: Any) -> None:
    events: List[PriceAlertEvent] = dl.price_alert_events.get_recent(limit=50)
    print()
    print("╭──────────── 🛰 Market Activity / XCom History ────────────╮")
    print("│  ⏱ Time (UTC)        🪙Asset  🧾Type    🧱State   💵Price   📊Move% │")
    print("╰────────────────────────────────────────────────────────────╯")

    if not events:
        print("  (no history yet – waiting for alerts to fire)")
    else:
        for ev in events:
            t = ev.created_at
            try:
                dt = datetime.fromisoformat(str(t))
                t_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                t_str = str(t)
            move_pct = ev.movement_percent or 0.0
            print(
                f"  {t_str}  {ev.asset:<5}  {ev.event_type:<8} "
                f"{(ev.state_after or ''):<6} {(ev.price_at_event or 0.0):>8.2f} "
                f"{move_pct:>7.2f}%"
            )

    input("\n⏎  Press ENTER to return...")


# ───────────────────── help ─────────────────────


def show_help() -> None:
    print()
    print("╭────────────────────── 📖 Help & Concepts ───────────────────────╮")
    print("│                                                                  │")
    print("│ • 🎯 Anchor: a remembered price used as the baseline for         │")
    print("│   movement alerts. 'Move 5% from anchor' compares current vs     │")
    print("│   this anchor price.                                             │")
    print("│                                                                  │")
    print("│ • 🎯 Threshold: how big a move you care about.                   │")
    print("│   – 📊 Percent move  (≥ X% from anchor)                          │")
    print("│   – 💵 Dollar move   (≥ $X from anchor)                          │")
    print("│   – 🎯 Target price  (crosses a fixed level)                     │")
    print("│                                                                  │")
    print("│ • ♻️ Recurrence: what happens after an alert fires:              │")
    print("│   – single : alert once, then disarmed until reset               │")
    print("│   – reset  : alert, then anchor jumps to the new price           │")
    print("│   – ladder : alert on each step of size threshold                │")
    print("│                                                                  │")
    print("│ • 🔁 Reset: re-arm an alert at the current price or at the       │")
    print("│   original anchor, restarting its \"distance to threshold\".      │")
    print("│                                                                  │")
    print("│ • 🔋 Proximity bar: shows how close the current move is to       │")
    print("│   the threshold. 0% = empty, 100% = alert fires.                 │")
    print("╰──────────────────────────────────────────────────────────────────╯")
    input("\n⏎  Press ENTER to return...")


if __name__ == "__main__":
    run_market_console()
