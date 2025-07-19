import asyncio
import os
import sys
from pathlib import Path
from uuid import uuid4

# NOTE: CycloneConsoleService is designed for interactive use.  Expose a helper
# function ``run_cyclone_console`` so callers don't need to manually construct a
# ``Cyclone`` instance.
from backend.core.cyclone_core.cyclone_engine import Cyclone
from backend.data.data_locker import DataLocker

from backend.core.cyclone_core.cyclone_engine import Cyclone
from backend.data.data_locker import DataLocker
from backend.core.locker_factory import get_locker

# Import HedgeManager from the actual implementation location
from backend.core.positions_core.hedge_manager import HedgeManager
from backend.core.logging import log
from backend.core.cyclone_core.cyclone_position_service import CyclonePositionService
from backend.core.cyclone_core.cyclone_portfolio_service import CyclonePortfolioService
# Alert V2 hybrid repo
from backend.alert_v2 import AlertRepo
from backend.alert_v2.models import (
    AlertConfig,
    Threshold,
    Condition,
    NotificationType,
)
from backend.core.cyclone_core.cyclone_alert_service import CycloneAlertService
from backend.core.cyclone_core.cyclone_hedge_service import CycloneHedgeService
from backend.core.cyclone_core.cyclone_report_generator import generate_cycle_report

class CycloneConsoleService:
    def __init__(self, cyclone_instance):
        self.cyclone = cyclone_instance
        self.position_service = CyclonePositionService(cyclone_instance.data_locker)
        self.portfolio_service = CyclonePortfolioService(cyclone_instance.data_locker)
        self.alert_service = CycloneAlertService(cyclone_instance.data_locker)
        self.alert_repo = AlertRepo()          # 🔔 NEW
        self.alert_repo.ensure_schema()  # 🔔 make sure alert_* tables exist
        self.hedge_service = CycloneHedgeService(cyclone_instance.data_locker)

    @staticmethod
    def _get(obj, key, default=None):
        """Safely fetch ``key`` from ``obj`` whether it is a dict or model."""
        return getattr(obj, key, default) if not isinstance(obj, dict) else obj.get(key, default)

    def run(self):
        """Backward compatible entry point."""
        self.run_console()


    def run_console(self):
        while True:
            print("\n=== Cyclone Interactive Console ===")
            print("1) 🌀 Run Full Cycle")
            print("2) 🗑️ Delete All Data")
            print("3) 💰 Prices")
            print("4) 📊 Positions")
            print("5) 🔔 Alerts")
            print("6) 🛡 Hedge")
            print("7) 🧹 Clear IDs")
            print("8) 💼 Wallets")
            print("9) 📝 Generate Cycle Report")
            print("10) ❌ Exit")
            choice = input("Enter your choice (1-10): ").strip()

            if choice == "1":
                print("Running full cycle (all steps)...")
                asyncio.run(self.cyclone.run_cycle())
                print("Full cycle completed.")
            elif choice == "2":
                self.cyclone.run_delete_all_data()
            elif choice == "3":
                self.run_prices_menu()
            elif choice == "4":
                self.run_positions_menu()
            elif choice == "5":
                self.run_alerts_menu()
            elif choice == "6":
                self.run_hedges_menu()
            elif choice == "7":
                print("Clearing stale IDs...")
                asyncio.run(self.cyclone.run_cleanse_ids())
            elif choice == "8":
                self.run_wallets_menu()
            elif choice == "9":
                print("Generating cycle report...")
                try:
                    generate_cycle_report()  # External report generator
                    self.cyclone.log_cyclone(
                        operation_type="Cycle Report Generated",
                        primary_text="Cycle report generated successfully",
                        source="Cyclone",
                        file="cyclone_engine.py",
                    )
                except Exception as e:
                    self.cyclone.logger.error(f"Cycle report generation failed: {e}", exc_info=True)
                    print(f"Cycle report generation failed: {e}")
            elif choice == "10":
                print("Exiting console mode.")
                break
            else:
                print("Invalid choice, please try again.")

    def run_prices_menu(self):
        while True:
            print("\n--- Prices Menu ---")
            print("1) 🚀 Market Update")
            print("2) 👁 View Prices")
            print("3) 🧹 Clear Prices")
            print("4) ↩️ Back to Main Menu")
            choice = input("Enter your choice (1-4): ").strip()
            if choice == "1":
                print("Running Market Update...")
                asyncio.run(self.cyclone.run_cycle(steps=["market_updates"]))
                print("Market Update completed.")
            elif choice == "2":
                print("Viewing Prices...")
                self.view_prices_backend()
            elif choice == "3":
                print("Clearing Prices...")
                self.cyclone.clear_prices_backend()
            elif choice == "4":
                break
            else:
                print("Invalid choice, please try again.")

    def run_positions_menu(self):
        while True:
            print("\n--- Positions Menu ---")
            print("1) 👁 View Positions")
            print("2) 🔄 Positions Updates")
            print("3) ✨ Enrich Positions")  # Renamed option for clarity
            print("4) 🧹 Clear Positions")
            print("5) ↩️ Back to Main Menu")
            choice = input("Enter your choice (1-5): ").strip()
            if choice == "1":
                print("Viewing Positions...")
                self.view_positions_backend()
            elif choice == "2":
                print("Running Position Updates...")
                asyncio.run(self.cyclone.run_position_updates())
                print("Position Updates completed.")
            elif choice == "3":
                print("Running Enrich Positions...")
                asyncio.run(self.cyclone.run_cycle(steps=["enrich_positions"]))
                print("Enrich Positions completed.")
            elif choice == "4":
                print("Clearing Positions...")
                #self.position_service.clear_positions_backend()
                asyncio.run(self.position_service.clear_positions_backend())

            elif choice == "5":
                break
            else:
                print("Invalid choice, please try again.")

        # In cyclone_console_helper.py (CycloneConsoleHelper class)

    def run_alerts_menu(self):
        while True:
            print("\n--- Alerts Menu (V2) ---")
            print("1) 👁 View Alerts")
            print("2) ➕ Create Alert")
            print("3) ✏️ Edit Alert Trigger")
            print("4) 🗑 Delete Alert")
            print("5) 📐 View Thresholds")
            print("6) ✏️ Edit Threshold")
            print("7) ↩️ Back to Main Menu")
            choice = input("Enter choice (1-7): ").strip()

            if choice == "1":
                self._view_alerts_v2()
            elif choice == "2":
                self._create_alert_v2()
            elif choice == "3":
                self._edit_alert_trigger_v2()
            elif choice == "4":
                self._delete_alert_v2()
            elif choice == "5":
                self._view_thresholds_v2()
            elif choice == "6":
                self._edit_threshold_v2()
            elif choice == "7":
                break
            else:
                print("Invalid choice.")

    def run_hedges_menu(self):
        """
        Display a submenu for managing hedge data with these options:
          1) View Hedges – display current hedge data using the HedgeManager.
          2) Find Hedges – run the HedgeManager.find_hedges method to scan positions and assign new hedge IDs.
          3) Clear Hedges – clear all hedge associations from the database.
          4) Back to Main Menu.
        """


        while True:
            print("\n--- Hedges Menu ---")
            print("1) 👁 View Hedges")
            print("2) 🔍 Find Hedges")
            print("3) 🧹 Clear Hedges")
            print("4) ↩️ Back to Main Menu")
            choice = input("Enter your choice (1-4): ").strip()

            if choice == "1":
                # View hedges using current positions
                dl = get_locker()
                raw_positions = dl.read_positions()
                hedge_manager = HedgeManager(raw_positions)
                hedges = hedge_manager.get_hedges()
                if hedges:
                    print("\nCurrent Hedges:")
                    for hedge in hedges:
                        print(f"Hedge ID: {hedge.id}")
                        print(f"  Positions: {hedge.positions}")
                        print(f"  Total Long Size: {hedge.total_long_size}")
                        print(f"  Total Short Size: {hedge.total_short_size}")
                        print(f"  Long Heat Index: {hedge.long_heat_index}")
                        print(f"  Short Heat Index: {hedge.short_heat_index}")
                        print(f"  Total Heat Index: {hedge.total_heat_index}")
                        print(f"  Notes: {hedge.notes}")
                        print("-" * 40)
                else:
                    print("No hedges found.")
            elif choice == "2":
                # Find hedges: use the static method that scans positions, updates hedge_buddy_id, and returns hedge groups.
                dl = get_locker()
                groups = HedgeManager.find_hedges()
                if groups:
                    print(f"Found {len(groups)} hedge group(s) after scanning positions:")
                    for idx, group in enumerate(groups, start=1):
                        print(f"Group {idx}:")
                        for pos in group:
                            pid = self._get(pos, 'id')
                            ptype = self._get(pos, 'position_type')
                            print(f"  Position ID: {pid} (Type: {ptype})")
                        print("-" * 30)
                else:
                    print("No hedge groups found.")
            elif choice == "3":
                # Clear hedges: clear hedge associations from all positions.
                try:
                    HedgeManager.clear_hedge_data()
                    print("Hedge associations cleared.")
                except Exception as e:
                    print(f"Error clearing hedges: {e}")
            elif choice == "4":
                break
            else:
                print("Invalid choice, please try again.")

    def run_wallets_menu(self):
        while True:
            print("\n--- Wallets Menu ---")
            print("1) 👁 View Wallets")
            print("2) ➕ Add Wallet")
            print("3) 🧹 Clear Wallets")
            print("4) ↩️ Back to Main Menu")
            choice = input("Enter your choice (1-4): ").strip()
            if choice == "1":
                print("Viewing Wallets...")
                self.cyclone.view_wallets_backend()
            elif choice == "2":
                print("Adding Wallet...")
                self.cyclone.add_wallet_backend()
            elif choice == "3":
                print("Clearing Wallets...")
                self.cyclone.clear_wallets_backend()
            elif choice == "4":
                break
            else:
                print("Invalid choice, please try again.")

    def view_price_details(self, price: dict):
        print("━━━━━━━━━━━━ PRICE ━━━━━━━━━━━━")
        print(f"🆔 ID:           {price.get('id', '')}")
        print(f"💰 Asset:        {price.get('asset_type', '')}")
        print(f"💵 Current:      {price.get('current_price', '')}")
        print(f"↩️ Previous:     {price.get('previous_price', '')}")
        print(f"📅 Last Update:  {price.get('last_update_time', '')}")
        print(f"⏪ Prev Update:  {price.get('previous_update_time', '')}")
        print(f"📡 Source:       {price.get('source', '')}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    def view_position_details(self, pos: dict):
        print("━━━━━━━━━━ POSITION ━━━━━━━━━━")
        print(f"🆔 ID:           {self._get(pos, 'id', '')}")
        print(f"💰 Asset:        {self._get(pos, 'asset_type', '')}")
        print(f"📉 Type:         {self._get(pos, 'position_type', '')}")
        print(f"📈 Entry Price:  {self._get(pos, 'entry_price', '')}")
        print(f"🔄 Current:      {self._get(pos, 'current_price', '')}")
        print(f"💣 Liq. Price:   {self._get(pos, 'liquidation_price', '')}")
        print(f"🪙 Collateral:   {self._get(pos, 'collateral', '')}")
        print(f"📦 Size:         {self._get(pos, 'size', '')}")
        print(f"⚖ Leverage:      {self._get(pos, 'leverage', '')}x")
        print(f"💵 Value:        {self._get(pos, 'value', '')}")
        print(f"💰 PnL (net):    {self._get(pos, 'pnl_after_fees_usd', '')}")
        print(f"💼 Wallet:       {self._get(pos, 'wallet_name', '')}")
        print(f"🧠 Alert Ref:    {self._get(pos, 'alert_reference_id', '')}")
        print(f"🛡 Hedge ID:     {self._get(pos, 'hedge_buddy_id', '')}")
        print(f"📅 Updated:      {self._get(pos, 'last_updated', '')}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    def view_alert_details(self, alert: dict):
        print("━━━━━━━━━━━━ ALERT ━━━━━━━━━━━━")
        print(f"🆔 ID:               {alert.get('id', '')}")
        print(f"📅 Created:          {alert.get('created_at', '')}")
        print(f"📣 Type:             {alert.get('alert_type', '')}")
        print(f"🎯 Class:            {alert.get('alert_class', '')}")
        print(f"🔔 Notify:           {alert.get('notification_type', '')}")
        print(f"📊 Trigger:          {alert.get('trigger_value', '')}")
        print(f"🧮 Evaluated Value:  {alert.get('evaluated_value', '')}")
        print(f"🟡 Status:           {alert.get('status', '')} | Level: {alert.get('level', '')}")
        print(f"📈 Counter/Freq:     {alert.get('counter', 0)} / {alert.get('frequency', 1)}")
        print(f"💣 Liq Distance:     {alert.get('liquidation_distance', '')}")
        print(f"📉 Travel %:         {alert.get('travel_percent', '')}")
        print(f"💥 Liq Price:        {alert.get('liquidation_price', '')}")
        print(f"🧠 Position Ref:     {alert.get('position_reference_id', '')}")
        print(f"📝 Notes:            {alert.get('notes', '')}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    # ─────────────────────────  V2 Helpers  ───────────────────────── #

    # ----- Alerts -----
    def _view_alerts_v2(self):
        alerts = [cfg.model_dump() | st.model_dump()
                  for cfg, st in self.alert_repo.iter_alerts_with_state()]
        self.paginate_items(alerts, self.view_alert_details, title="Alert V2 Configs")

    def _create_alert_v2(self):
        aid = input("Alert ID (blank = auto): ").strip() or f"alert-{uuid4()}"

        alert_types = ["TravelPercent", "PriceThreshold", "Profit", "LiquidationDistance"]
        print("\nChoose Alert Type:")
        for i, at in enumerate(alert_types, 1):
            print(f"{i}) {at}")
        while True:
            try:
                at_choice = int(input("Enter choice number: "))
                alert_type = alert_types[at_choice - 1]
                break
            except (IndexError, ValueError):
                print("Invalid selection. Try again.")

        alert_classes = ["Position", "Portfolio", "Market"]
        print("\nChoose Alert Class:")
        for i, ac in enumerate(alert_classes, 1):
            print(f"{i}) {ac}")
        while True:
            try:
                ac_choice = int(input("Enter choice number: "))
                alert_class = alert_classes[ac_choice - 1]
                break
            except (IndexError, ValueError):
                print("Invalid selection. Try again.")

        while True:
            try:
                trig = float(input("Trigger Value (must be positive): "))
                if trig <= 0:
                    raise ValueError
                break
            except ValueError:
                print("Trigger Value must be a positive number. Try again.")

        conditions = ["ABOVE", "BELOW"]
        print("\nChoose Condition:")
        for i, cond in enumerate(conditions, 1):
            print(f"{i}) {cond}")
        while True:
            try:
                cond_choice = int(input("Enter choice number: "))
                condition = Condition[conditions[cond_choice - 1]]
                break
            except (IndexError, ValueError):
                print("Invalid selection. Try again.")

        notifications = ["SMS", "EMAIL"]
        print("\nChoose Notification Type:")
        for i, nt in enumerate(notifications, 1):
            print(f"{i}) {nt}")
        while True:
            try:
                nt_choice = int(input("Enter choice number: "))
                notification_type = NotificationType[notifications[nt_choice - 1]]
                break
            except (IndexError, ValueError):
                print("Invalid selection. Try again.")

        pos_ref = input("Position Ref ID (blank if N/A): ").strip() or None

        cfg = AlertConfig(
            id=aid,
            alert_type=alert_type,
            alert_class=alert_class,
            trigger_value=trig,
            condition=condition,
            notification_type=notification_type,
            position_reference_id=pos_ref,
        )
        self.alert_repo.add_config(cfg)
        print(f"✅ Alert '{aid}' created successfully.")

    def _edit_alert_trigger_v2(self):
        aid = input("Alert ID to edit: ").strip()
        cfg = self.alert_repo.get_config(aid)
        if not cfg:
            print("⚠️ Not found.")
            return
        new_val = float(input(f"New trigger (current {cfg.trigger_value}): "))
        cfg_dict = cfg.model_dump()
        cfg_dict["trigger_value"] = new_val
        # replace = delete & re‑add (simplest for frozen model)
        self.alert_repo.session.execute(
            "DELETE FROM alert_config WHERE id = :id", {"id": aid}
        )
        self.alert_repo.session.commit()
        self.alert_repo.add_config(AlertConfig(**cfg_dict))
        print("✅ Trigger updated.")

    def _delete_alert_v2(self):
        aid = input("Alert ID to delete: ").strip()
        self.alert_repo.session.execute(
            "DELETE FROM alert_config WHERE id = :id", {"id": aid}
        )
        self.alert_repo.session.execute(
            "DELETE FROM alert_state  WHERE alert_id = :id", {"id": aid}
        )
        self.alert_repo.session.commit()
        print("🗑 Alert removed.")

    # ----- Thresholds -----
    def _view_thresholds_v2(self):
        rows = self.alert_repo.session.execute("SELECT * FROM alert_threshold").fetchall()
        if not rows:
            print("⚠️ No thresholds.")
            return
        for r in rows:
            print(f"{r.id} | {r.alert_type}/{r.alert_class} "
                  f"low={r.low} med={r.medium} high={r.high} enabled={r.enabled}")

    def _edit_threshold_v2(self):
        tid = input("Threshold ID to edit: ").strip()
        row = self.alert_repo.session.execute(
            "SELECT * FROM alert_threshold WHERE id=:id", {"id": tid}
        ).first()
        if not row:
            print("⚠️ Not found.")
            return
        new_low = input(f"Low ({row.low}): ").strip() or row.low
        new_med = input(f"Med ({row.medium}): ").strip() or row.medium
        new_high= input(f"High({row.high}): ").strip() or row.high
        enabled = input(f"Enabled(y/n) [{ 'y' if row.enabled else 'n' }]: ").strip().lower()
        en_bool = row.enabled if enabled not in ("y", "n") else enabled == "y"

        self.alert_repo.session.execute(
            """
            UPDATE alert_threshold
            SET low=:low, medium=:med, high=:high, enabled=:en
            WHERE id=:id
            """,
            dict(low=float(new_low), med=float(new_med),
                 high=float(new_high), en=en_bool, id=tid),
        )
        self.alert_repo.session.commit()
        print("✅ Threshold updated.")

    def paginate_items(self, items: list, display_fn: callable, title: str = "", page_size: int = 5):
        """
        🧾 Paginate and display a list of items using a display function.
        """
        if not items:
            print("⚠️ No records to display.")
            return

        index = 0
        total = len(items)
        total_pages = (total + page_size - 1) // page_size

        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            current_page = (index // page_size) + 1
            print(f"\n📄 {title} — Showing {index + 1}-{min(index + page_size, total)} of {total}\n")

            for i in range(index, min(index + page_size, total)):
                display_fn(items[i])

            # Footer
            print(f"\n📘 Page {current_page} of {total_pages}")
            print("Commands: [N]ext | [P]rev | [Q]uit | [Enter]=Next/Quit")

            cmd = input("→ ").strip().lower()

            if cmd == "n":
                if index + page_size < total:
                    index += page_size
                else:
                    print("⚠️ Already on last page.")
            elif cmd == "p":
                if index - page_size >= 0:
                    index -= page_size
                else:
                    print("⚠️ Already on first page.")
            elif cmd == "q":
                break
            elif cmd == "":
                if index + page_size < total:
                    index += page_size
                else:
                    break  # treat Enter on last page as Quit
            else:
                print("⚠️ Invalid input.")

    def view_prices_backend(self):
        prices = self.cyclone.data_locker.prices.get_all_prices()
        self.paginate_items(prices, self.view_price_details, title="Latest Prices")

    def view_positions_backend(self):
        print("👁 [DEBUG] Viewer using DB path:", self.cyclone.data_locker.db.db_path)

        positions = self.cyclone.data_locker.positions.get_all_positions()

        if not positions:
            print("⚠️ No positions found in DB.")
        else:
            print(f"🧾 DEBUG: Pulled {len(positions)} positions from DB:")
            for pos in positions:
                pid = self._get(pos, 'id')
                asset = self._get(pos, 'asset_type')
                wallet = self._get(pos, 'wallet_name')
                print(f"  ➤ {pid} — {asset} — {wallet}")

        self.paginate_items(positions, self.view_position_details, title="Open Positions")


    def view_alerts_backend(self):
        alerts = self.cyclone.data_locker.alerts.get_all_alerts()
        self.paginate_items(alerts, self.view_alert_details, title="Alert Definitions")


def run_cyclone_console(poll_interval: int = 60) -> None:
    """Launch :class:`CycloneConsoleService` with a fresh ``Cyclone`` instance."""
    cyclone = Cyclone(poll_interval=poll_interval)
    service = CycloneConsoleService(cyclone)
    service.run_console()


if __name__ == "__main__":
    from backend.core.cyclone_core.cyclone_engine import Cyclone

    from backend.core.locker_factory import get_locker
    cyclone = Cyclone(poll_interval=60)
    helper = CycloneConsoleService(cyclone)
    helper.run_console()
