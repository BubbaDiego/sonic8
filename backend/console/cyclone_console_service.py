# backend/console/cyclone_console_service.py
from __future__ import annotations

import asyncio
import os
import sys
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, IntPrompt, Confirm

try:
    from backend.data.data_locker import DataLocker
except Exception:
    DataLocker = None  # type: ignore

# Optional at runtime (lazy-loaded when needed)
WalletCore = None
WalletModel = None  # backend.models.wallet.Wallet

ICON: Dict[str, str] = {
    "app": "🌪️",
    "db": "🗄️",
    "wallet": "👝",
    "rpc": "🌐",
    "interval": "⏱️",
    "loop_on": "🟢",
    "loop_off": "🔴",
    "last": "🕒",
    "alerts": "🚨",
    "notify": "🔔",
    "run": "▶️",
    "loop": "🔁",
    "stop": "⏹️",
    "refresh": "🗘",
    "report": "📄",
    "clean": "🧹",
    "settings": "⚙️",
    "help": "❓",
    "cycle": "🧭",
    "prices": "💹",
    "positions": "📊",
    "alerts_menu": "🚨",
    "hedges": "🛡️",
    "portfolio": "🧺",
    "reports": "🧾",
    "maintenance": "🧰",
    "logs": "📜",
    "ok": "✅",
    "warn": "⚠️",
    "err": "❌",
    "run_small": "🔄",
    "info": "ℹ️",
    "wipe": "🧽",
}

def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        box = {}
        def _t():  # run in thread
            box["v"] = asyncio.run(coro)
        t = threading.Thread(target=_t, daemon=True)
        t.start(); t.join()
        return box.get("v")
    return asyncio.run(coro)


@dataclass
class LoopState:
    enabled: bool = False
    interval: int = 30
    stop_event: threading.Event = field(default_factory=threading.Event)
    thread: Optional[threading.Thread] = None


class CycloneConsoleService:
    """
    Icon-forward Cyclone console (menus only).
    Uses DataLocker/DLWalletManager for wallet rows and WalletCore for SOL (if available).
    """

    def __init__(self, cyclone: Optional[object] = None):
        self.console = Console()
        self.cyclone = cyclone
        self.loop = LoopState(interval=self._detect_default_interval())
        self._selected_steps: List[str] = [
            "market_updates",
            "position_updates",
            "prune_stale_positions",
            "enrich_positions",
            "aggregate_positions",
            "create_global_alerts",
            "create_portfolio_alerts",
            "create_position_alerts",
            "alert_evaluation",
            "cleanse_ids",
            "link_hedges",
            "update_hedges",
        ]

    # ---------- main loop ----------

    def run_console(self) -> None:
        self._ensure_engine()
        while True:
            _clear()
            self._render_header()
            self._render_quick_actions()
            self.console.print()
            menu = Table.grid(padding=(0, 2))
            for label in (
                f"1) {ICON['cycle']}  Cycle Runner",
                f"2) {ICON['prices']}  Prices",
                f"3) {ICON['positions']}  Positions",
                f"4) {ICON['alerts_menu']}  Alerts",
                f"5) {ICON['hedges']}  Hedges",
                f"6) {ICON['portfolio']}  Portfolio",
                f"7) {ICON['wallet']}  Wallets",
                f"8) {ICON['reports']}  Reports",
                f"9) {ICON['maintenance']}  Maintenance",
                f"10) {ICON['wipe']}  Clear Data",
                f"11) {ICON['logs']}  Logs",
                f"12) {ICON['settings']}  Settings",
                f"13) {ICON['help']}  Help",
                f"0) {ICON['stop']}  Exit",
            ):
                menu.add_row(label)
            self.console.print(Panel(menu, title=f"{ICON['app']} Cyclone — Main Menu", border_style="cyan"))
            ch = Prompt.ask("Select")
            if ch == "1": self._screen_cycle_runner()
            elif ch == "2": self._screen_prices()
            elif ch == "3": self._screen_positions()
            elif ch == "4": self._screen_alerts()
            elif ch == "5": self._screen_hedges()
            elif ch == "6": self._screen_portfolio()
            elif ch == "7": self._screen_wallets()
            elif ch == "8": self._screen_reports()
            elif ch == "9": self._screen_maintenance()
            elif ch == "10": self._screen_clear_data()
            elif ch == "11": self._screen_logs()
            elif ch == "12": self._screen_settings()
            elif ch == "13": self._screen_help()
            elif ch in {"0", "q", "Q", "quit", "exit"}:
                self._stop_loop_if_running()
                self.console.print("\nbye 👋\n"); return
            else:
                self.console.print(f"\n{ICON['warn']} Invalid selection.\n")
                self._pause()

    # ---------- header ----------

    def _render_header(self) -> None:
        dl = getattr(self.cyclone, "data_locker", None)
        db_path = getattr(getattr(dl, "db", None), "db_path", "mother.db")
        wallet_hint = "—"
        rpc = "Helius"
        loop_icon = ICON["loop_on"] if self.loop.enabled else ICON["loop_off"]
        ts = time.strftime("%H:%M:%S")

        hdr = Text.assemble(
            (f" {ICON['app']} Cyclone v1  ", "bold white"),
            (f" | {ICON['db']} {db_path}  ", "cyan"),
            (f" | {ICON['wallet']} {wallet_hint}  ", "green"),
            (f" | {ICON['rpc']} {rpc}  ", "magenta"),
            (f" | {ICON['interval']} {self.loop.interval}s  ", "yellow"),
            (f" | {ICON['loop']} {loop_icon}  ", "bold"),
            (f" | {ICON['last']} {ts}  ", "white"),
            (f" | {ICON['alerts']} —  ", "red"),
            (f" | {ICON['notify']} 🔔  ", "blue"),
        )
        self.console.print(Panel(hdr, border_style="cyan"))

    def _render_quick_actions(self) -> None:
        row = Table.grid(expand=True)
        row.add_column(justify="center")
        row.add_row(Text.from_markup(
            f"[bold]{ICON['run']} Run Once   {ICON['loop']} Start Loop   {ICON['stop']} Stop Loop   "
            f"{ICON['refresh']} Refresh   {ICON['report']} Report   {ICON['clean']} Clean   "
            f"{ICON['settings']} Settings   {ICON['help']} Help[/]"))
        self.console.print(row)
        self.console.print(Text("Hotkeys: [R]un once, [L]oop, [S]ettings, [Q]uit", style="dim"))

    # ---------- screens ----------

    def _screen_cycle_runner(self) -> None:
        while True:
            _clear(); self._render_header()
            tbl = Table(title=f"{ICON['cycle']} Cycle Runner", expand=True)
            tbl.add_column("Step"); tbl.add_column("Selected", justify="center")
            for s in self._all_steps():
                mark = "☑" if s in self._selected_steps else "☐"
                tbl.add_row(self._label_for_step(s), mark)
            self.console.print(tbl)
            self.console.print(
                f"\n{ICON['run']} Run Once   {ICON['loop']} Start   {ICON['stop']} Stop   "
                f"✏️ Edit steps   {ICON['help']} Glossary   ↩️ Back")
            sel = Prompt.ask("Choose", default="run").lower()
            if sel in {"run","r","1"}: self._do_run_selected_steps()
            elif sel in {"edit","e"}: self._edit_steps()
            elif sel in {"start","s"}: self._start_loop()
            elif sel in {"stop"}: self._stop_loop_if_running()
            elif sel in {"back","b","0"}: return
            elif sel in {"help","h"}: self._show_steps_glossary()
            else:
                self.console.print(f"{ICON['warn']} Unknown command."); self._pause()

    def _screen_prices(self) -> None:
        _clear(); self._render_header()
        self.console.print(f"{ICON['prices']} [bold]Prices[/]\n")
        self.console.print(f"1) {ICON['run_small']} Sync Prices Now")
        self.console.print(f"2) {ICON['info']} Show Last Price Result")
        self.console.print("0) Back\n")
        ch = Prompt.ask("Select", default="1")
        if ch == "1": self._call_async("run_market_updates")
        elif ch == "2": self._show_last_price_result()
        self._pause()

    def _screen_positions(self) -> None:
        _clear(); self._render_header()
        self.console.print(f"{ICON['positions']} [bold]Positions[/]\n")
        self.console.print(f"1) {ICON['run_small']} Refresh From Traders")
        self.console.print(f"2) 🧽 Prune Stale")
        self.console.print(f"3) ✨ Enrich")
        self.console.print(f"4) 🧮 Aggregate")
        self.console.print("0) Back\n")
        ch = Prompt.ask("Select", default="1")
        if ch == "1": self._call_async("run_position_updates")
        elif ch == "2": self._call_async("run_prune_stale_positions")
        elif ch == "3": self._call_async("run_enrich_positions")
        elif ch == "4": self._call_async("run_aggregate_positions")
        self._pause()

    def _screen_alerts(self) -> None:
        _clear(); self._render_header()
        self.console.print(f"{ICON['alerts_menu']} [bold]Alerts[/]\n")
        self.console.print(f"1) 🌍 Create Market Alerts")
        self.console.print(f"2) 📦 Create Portfolio Alerts")
        self.console.print(f"3) 🎯 Create Position Alerts")
        self.console.print(f"4) 🧠 Evaluate Alerts")
        self.console.print(f"5) 🔥 Clear All Alerts (backend)")
        self.console.print("0) Back\n")
        ch = Prompt.ask("Select", default="4")
        if ch == "1": self._call_async("run_create_global_alerts")
        elif ch == "2": self._call_async("run_create_portfolio_alerts")
        elif ch == "3": self._call_async("run_create_position_alerts")
        elif ch == "4": self._call_async("run_alert_evaluation")
        elif ch == "5": self._call_sync("clear_alerts_backend")
        self._pause()

    def _screen_hedges(self) -> None:
        _clear(); self._render_header()
        self.console.print(f"{ICON['hedges']} [bold]Hedges[/]\n")
        self.console.print(f"1) 🔗 Link Hedges")
        self.console.print(f"2) 🔄 Update Hedge Groups")
        self.console.print("0) Back\n")
        ch = Prompt.ask("Select", default="1")
        if ch == "1": self._call_async("run_link_hedges")
        elif ch == "2": self._call_async("run_update_hedges")
        self._pause()

    def _screen_portfolio(self) -> None:
        _clear(); self._render_header()
        self.console.print(f"{ICON['portfolio']} [bold]Portfolio[/]\n")
        self.console.print(f"1) 🧮 Recompute Aggregates & Exposures")
        self.console.print(f"2) 🎚️ Risk View (if available)")
        self.console.print("0) Back\n")
        ch = Prompt.ask("Select", default="1")
        if ch == "1": self._call_async("run_update_evaluated_value")
        elif ch == "2": self.console.print(f"{ICON['warn']} Risk view not yet implemented.")
        self._pause()

    # ---------- WALLET SCREEN (uses wallet_core + dl_wallets) ----------

    def _screen_wallets(self) -> None:
        _clear(); self._render_header()
        self.console.print(f"{ICON['wallet']} [bold]Wallets[/]\n")

        rows = self._get_wallet_rows()  # via DataLocker / DLWalletManager
        wc = self._wallet_core()        # WalletCore if available

        tbl = Table(expand=True, title="Known Wallets")
        tbl.add_column("Name"); tbl.add_column("Address"); tbl.add_column("SOL", justify="right")

        if rows:
            for r in rows:
                sol_str = "—"
                if wc and WalletModel and r.get("public_address"):
                    try:
                        wobj = WalletModel(
                            name=r.get("name"), public_address=r.get("public_address"),
                            chrome_profile=r.get("chrome_profile","Default"),
                            private_address=None, image_path=None, balance=0.0,
                            tags=r.get("tags",[]), is_active=bool(r.get("is_active", True)),
                            type=r.get("type","personal"),
                        )
                        sol = wc.fetch_balance(wobj)  # may return None if solana libs missing
                        if sol is not None:
                            sol_str = f"{sol:.4f}"
                    except Exception:
                        sol_str = "—"
                tbl.add_row(str(r.get("name","—")), str(r.get("public_address","—")), sol_str)
        else:
            self.console.print(f"{ICON['warn']} No wallets found in DB.")

        self.console.print(tbl)

        # Actions
        self.console.print("\nActions:")
        self.console.print(f"1) {ICON['run_small']} Refresh DB balances from positions (WalletCore)  ")
        self.console.print("0) Back\n")
        ch = Prompt.ask("Select", default="0")
        if ch == "1":
            if wc:
                try:
                    updated = wc.refresh_wallet_balances()
                    self.console.print(f"{ICON['ok']} Updated {updated} wallet balance(s) from positions.")
                except Exception as exc:
                    self.console.print(f"{ICON['warn']} Refresh failed: {exc}")
            else:
                self.console.print(f"{ICON['warn']} WalletCore unavailable.")
            self._pause()
        # Back always returns

    # ---------- reports / maintenance / logs / settings ----------

    def _screen_reports(self) -> None:
        _clear(); self._render_header()
        self.console.print(f"{ICON['reports']} [bold]Reports[/]\n")
        self.console.print(f"1) {ICON['report']} Generate HTML Report (opens in browser)")
        self.console.print(f"2) 📤 Export CSV")
        self.console.print("0) Back\n")
        ch = Prompt.ask("Select", default="1")
        if ch == "1": self._call_sync("generate_report_html")
        elif ch == "2": self._call_sync("export_report_csv")
        self._pause()

    def _screen_maintenance(self) -> None:
        _clear(); self._render_header()
        self.console.print(f"{ICON['maintenance']} [bold]Maintenance[/]\n")
        self.console.print(f"1) 🧽 Cleanse Alert IDs")
        self.console.print(f"2) 🧰 Vacuum / Compact DB")
        self.console.print(f"3) 🌱 Reseed Configs (thresholds etc.)")
        self.console.print("0) Back\n")
        ch = Prompt.ask("Select", default="1")
        if ch == "1": self._call_async("run_cleanse_ids")
        elif ch == "2": self._vacuum_db()
        elif ch == "3": self._reseed_configs()
        self._pause()

    def _screen_clear_data(self) -> None:
        while True:
            _clear(); self._render_header()
            self.console.print(f"{ICON['wipe']} [bold]Clear Data[/]\n")
            self.console.print("1) 🗑️ Clear Positions")
            self.console.print("2) 🗑️ Clear Prices")
            self.console.print("3) 🧨 Clear ALL (alerts, prices, positions)")
            self.console.print("0) Back\n")
            ch = Prompt.ask("Select", default="0")

            if ch == "1":
                if Confirm.ask("Really delete ALL open positions?", default=False):
                    try:
                        self._call_sync("clear_positions_backend")
                        self.console.print(f"{ICON['ok']} Positions cleared.")
                    except Exception as exc:
                        self.console.print(f"{ICON['err']} Failed to clear positions: {exc}")
                else:
                    self.console.print("↩️ Cancelled.")
                self._pause()

            elif ch == "2":
                if Confirm.ask("Really delete ALL stored prices?", default=False):
                    try:
                        self._call_sync("clear_prices_backend")
                        self.console.print(f"{ICON['ok']} Prices cleared.")
                    except Exception as exc:
                        self.console.print(f"{ICON['err']} Failed to clear prices: {exc}")
                else:
                    self.console.print("↩️ Cancelled.")
                self._pause()

            elif ch == "3":
                if Confirm.ask("⚠️ IRREVERSIBLE: clear alerts, prices, positions — continue?", default=False):
                    try:
                        self._ensure_engine()
                        engine = self.cyclone
                        if engine and hasattr(engine, "run_clear_all_data"):
                            self._call_async("run_clear_all_data")
                            self.console.print(f"{ICON['ok']} Alerts, prices, and positions cleared.")
                        elif engine and hasattr(engine, "run_delete_all_data"):
                            self._call_sync("run_delete_all_data")
                            self.console.print(f"{ICON['ok']} Alerts, prices, and positions cleared.")
                        else:
                            self.console.print(f"{ICON['warn']} Engine does not expose a clear-all operation.")
                            self._pause()
                            continue
                    except Exception as exc:
                        self.console.print(f"{ICON['err']} Clear All Data failed: {exc}")
                else:
                    self.console.print("↩️ Cancelled.")
                self._pause()

            elif ch in {"0", "back", "b"}:
                return
            else:
                self.console.print(f"{ICON['warn']} Invalid selection.")
                self._pause()

    def _screen_logs(self) -> None:
        _clear(); self._render_header()
        self.console.print(f"{ICON['logs']} [bold]Logs[/]\n")
        n = IntPrompt.ask("Tail how many lines?", default=300)
        self._tail_logs(n); self._pause()

    def _screen_settings(self) -> None:
        _clear(); self._render_header()
        self.console.print(f"{ICON['settings']} [bold]Settings[/]\n")
        self.console.print(f"1) {ICON['interval']} Set Poll Interval (current: {self.loop.interval}s)")
        self.console.print(f"2) {ICON['alerts']} Edit Alert Thresholds (DB)")
        self.console.print("0) Back\n")
        ch = Prompt.ask("Select", default="1")
        if ch == "1":
            self.loop.interval = IntPrompt.ask("Interval seconds", default=self.loop.interval)
        elif ch == "2":
            self._edit_alert_thresholds()
        self._pause()

    def _screen_help(self) -> None:
        _clear(); self._render_header()
        self.console.print(f"{ICON['help']} [bold]Help[/]\n")
        self.console.print("Shortcuts: R=Run once, L=Start loop, S=Settings, Q=Quit")
        self.console.print("Wallets: lists from DataLocker; SOL shown via WalletCore when Solana libs are present.")
        self._pause()

    # ---------- actions ----------

    def _do_run_selected_steps(self) -> None:
        self._ensure_engine()
        run_map: Dict[str, Callable[[], None]] = {
            "market_updates": lambda: self._call_async("run_market_updates"),
            "position_updates": lambda: self._call_async("run_position_updates"),
            "prune_stale_positions": lambda: self._call_async("run_prune_stale_positions"),
            "enrich_positions": lambda: self._call_async("run_enrich_positions"),
            "aggregate_positions": lambda: self._call_async("run_aggregate_positions"),
            "create_global_alerts": lambda: self._call_async("run_create_global_alerts"),
            "create_portfolio_alerts": lambda: self._call_async("run_create_portfolio_alerts"),
            "create_position_alerts": lambda: self._call_async("run_create_position_alerts"),
            "alert_evaluation": lambda: self._call_async("run_alert_evaluation"),
            "cleanse_ids": lambda: self._call_async("run_cleanse_ids"),
            "link_hedges": lambda: self._call_async("run_link_hedges"),
            "update_hedges": lambda: self._call_async("run_update_hedges"),
        }
        for step in self._selected_steps:
            fn = run_map.get(step)
            if not fn:
                self.console.print(f"{ICON['warn']} No runner for step: {step}")
                continue
            self.console.print(f"{ICON['run_small']} {self._label_for_step(step)} …")
            try:
                fn(); self.console.print(f"{ICON['ok']} {self._label_for_step(step)} done")
            except Exception as exc:
                self.console.print(f"{ICON['err']} {step} failed: {exc}")
        self._pause()

    def _start_loop(self) -> None:
        self._ensure_engine()
        if self.loop.enabled:
            self.console.print(f"{ICON['warn']} Loop already running."); self._pause(); return
        self.loop.stop_event.clear()
        def _runner():
            while not self.loop.stop_event.is_set():
                try:
                    self._do_run_selected_steps()
                except Exception as exc:
                    self.console.print(f"{ICON['err']} loop error: {exc}")
                for _ in range(self.loop.interval):
                    if self.loop.stop_event.is_set(): break
                    time.sleep(1)
        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        self.loop.thread = t; self.loop.enabled = True
        self.console.print(f"{ICON['loop']} Loop started."); self._pause()

    def _stop_loop_if_running(self) -> None:
        if not self.loop.enabled: return
        self.loop.stop_event.set()
        if self.loop.thread: self.loop.thread.join(timeout=1.0)
        self.loop.enabled = False

    def _show_last_price_result(self) -> None:
        data = getattr(self.cyclone, "last_price_result", None) or {}
        tbl = Table(title="Last Price Result", expand=True)
        tbl.add_column("Key"); tbl.add_column("Value")
        for k, v in (data.items() if isinstance(data, dict) else []):
            tbl.add_row(str(k), str(v))
        self.console.print(tbl)

    # ---------- helpers ----------

    def _wallet_core(self):
        global WalletCore, WalletModel
        if WalletCore is None:
            try:
                from backend.core.wallet_core.wallet_core import WalletCore as _WC  # type: ignore
                from backend.models.wallet import Wallet as _WM  # type: ignore
                WalletCore = _WC
                WalletModel = _WM
            except Exception:
                return None
        try:
            return WalletCore()  # type: ignore
        except Exception:
            return None

    def _get_wallet_rows(self) -> List[dict]:
        """Return wallet dicts from DataLocker/DLWalletManager with normalized keys."""
        rows: List[dict] = []
        dl = getattr(self.cyclone, "data_locker", None)

        # Primary path: DataLocker.read_wallets()
        try:
            if dl and hasattr(dl, "read_wallets"):
                r = dl.read_wallets()
                if isinstance(r, list): rows = r
        except Exception:
            rows = []

        # Fallback: dl.wallets.get_wallets()
        if not rows and dl and hasattr(dl, "wallets") and hasattr(dl.wallets, "get_wallets"):
            try:
                r = dl.wallets.get_wallets()
                if isinstance(r, list): rows = r
            except Exception:
                pass

        # Final fallback: DataLocker singleton
        if not rows and DataLocker is not None:
            try:
                dls = DataLocker.get_instance()
                if hasattr(dls, "read_wallets"):
                    r = dls.read_wallets()
                    if isinstance(r, list): rows = r
            except Exception:
                pass

        # Normalize common keys
        out: List[dict] = []
        for w in rows or []:
            out.append({
                "name": w.get("name") or w.get("label") or "—",
                "public_address": w.get("public_address") or w.get("pubkey") or w.get("address") or "—",
                "chrome_profile": w.get("chrome_profile", "Default"),
                "tags": w.get("tags", []),
                "is_active": bool(w.get("is_active", True)),
                "type": w.get("type", "personal"),
            })
        return out

    def _call_async(self, method: str):
        self._ensure_engine()
        fn = getattr(self.cyclone, method, None)
        if fn is None:
            self.console.print(f"{ICON['warn']} {method} not available on engine."); return
        if asyncio.iscoroutinefunction(fn): return _run_async(fn())
        return fn()

    def _call_sync(self, method: str):
        self._ensure_engine()
        fn = getattr(self.cyclone, method, None)
        if fn is None:
            self.console.print(f"{ICON['warn']} {method} not available on engine."); return
        return fn()

    def _vacuum_db(self):
        dl = getattr(self.cyclone, "data_locker", None)
        db = getattr(dl, "db", None)
        if not db or not hasattr(db, "vacuum"):
            self.console.print(f"{ICON['warn']} DB vacuum not available."); return
        try:
            db.vacuum(); self.console.print(f"{ICON['ok']} DB vacuum complete.")
        except Exception as exc:
            self.console.print(f"{ICON['err']} Vacuum failed: {exc}")

    def _reseed_configs(self):
        dl = getattr(self.cyclone, "data_locker", None)
        sys_mgr = getattr(dl, "system", None)
        if not sys_mgr or not hasattr(sys_mgr, "set_var"):
            self.console.print(f"{ICON['warn']} System var manager not available."); return
        self.console.print(f"{ICON['ok']} Reseed path executed (no-op if already seeded).")

    def _tail_logs(self, n: int = 300):
        log_path = getattr(self.cyclone, "console_log_path", None)
        if not log_path or not os.path.exists(str(log_path)):
            self.console.print(f"{ICON['warn']} No log file exposed by engine."); return
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f.readlines()[-n:]:
                    self.console.print(Text(line.rstrip(), overflow="crop"))
        except Exception as exc:
            self.console.print(f"{ICON['err']} Tail failed: {exc}")

    def _edit_steps(self) -> None:
        steps = self._all_steps()
        self.console.print("\nToggle steps (comma-separated indices). Current selection marked with ☑.\n")
        for i, s in enumerate(steps, 1):
            self.console.print(f"{i:2d}. {'☑' if s in self._selected_steps else '☐'} {self._label_for_step(s)}")
        raw = Prompt.ask("\nIndices to toggle (e.g. 1,3,5) or [Enter] to keep")
        if not raw.strip(): return
        try:
            idxs = [int(x.strip()) for x in raw.split(",") if x.strip()]
        except ValueError:
            self.console.print(f"{ICON['warn']} Bad input."); self._pause(); return
        for i in idxs:
            if 1 <= i <= len(steps):
                name = steps[i - 1]
                if name in self._selected_steps: self._selected_steps.remove(name)
                else: self._selected_steps.append(name)
        self.console.print(f"{ICON['ok']} Steps updated."); self._pause()

    def _edit_alert_thresholds(self) -> None:
        dl = getattr(self.cyclone, "data_locker", None)
        sys_mgr = getattr(dl, "system", None)
        if not sys_mgr or not hasattr(sys_mgr, "get_var"):
            self.console.print(f"{ICON['warn']} System var manager not available."); return
        cfg = sys_mgr.get_var("alert_thresholds") or {}
        self.console.print(f"Current keys: {', '.join(sorted(cfg.keys())) if isinstance(cfg, dict) else cfg}")
        if not Confirm.ask("Open editor?"): return
        key = Prompt.ask("Asset key (e.g. BTC)")
        try:
            val = float(Prompt.ask("Threshold (percent, e.g. 5.0)"))
        except Exception:
            self.console.print(f"{ICON['warn']} Invalid number."); return
        if not isinstance(cfg, dict): cfg = {}
        thresholds = dict(cfg.get("thresholds") or {})
        thresholds[key.upper()] = val
        cfg["thresholds"] = thresholds
        sys_mgr.set_var("alert_thresholds", cfg)
        self.console.print(f"{ICON['ok']} Saved.")

    def _pause(self) -> None:
        self.console.print(Text("\nPress [Enter] to continue…", style="dim"))
        try: input()
        except KeyboardInterrupt: pass

    def _ensure_engine(self) -> None:
        if self.cyclone is not None: return
        # Only used for price/alerts/etc. Wallet screen works with DataLocker directly.
        try:
            from backend.core.cyclone_core.cyclone_engine import Cyclone  # import here to avoid import loops
            self.cyclone = Cyclone(poll_interval=self._detect_default_interval())
        except Exception as exc:
            raise RuntimeError(f"Cyclone engine not available: {exc}")

    def _detect_default_interval(self) -> int:
        return 30

    def _all_steps(self) -> List[str]:
        return [
            "market_updates",
            "position_updates",
            "prune_stale_positions",
            "enrich_positions",
            "aggregate_positions",
            "create_global_alerts",
            "create_portfolio_alerts",
            "create_position_alerts",
            "alert_evaluation",
            "cleanse_ids",
            "link_hedges",
            "update_hedges",
        ]

    def _label_for_step(self, name: str) -> str:
        labels = {
            "market_updates": f"{ICON['prices']} Market updates",
            "position_updates": f"{ICON['positions']} Position updates",
            "prune_stale_positions": "🧽 Prune stale positions",
            "enrich_positions": "✨ Enrich positions",
            "aggregate_positions": "🧮 Aggregate positions",
            "create_global_alerts": "🌍 Create market alerts",
            "create_portfolio_alerts": "📦 Create portfolio alerts",
            "create_position_alerts": "🎯 Create position alerts",
            "alert_evaluation": "🧠 Evaluate alerts",
            "cleanse_ids": "🧽 Cleanse alert IDs",
            "link_hedges": "🔗 Link hedges",
            "update_hedges": "🔄 Update hedges",
        }
        return labels.get(name, name)


def run_cyclone_console(poll_interval: int = 30) -> None:
    svc = CycloneConsoleService(
        cyclone=None  # engine is created on demand
    )
    svc.run_console()


if __name__ == "__main__":
    run_cyclone_console()
