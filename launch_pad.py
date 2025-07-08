#!/usr/bin/env python3
"""
🚀 Sonic Launch Pad Console Enhanced
Enhanced console with pyfiglet title, custom emojis, numbers as strings, and launch flare.
"""

import subprocess
import webbrowser
import time
import sys
import os
import platform
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from pyfiglet import Figlet
from backend.console.cyclone_console_service import run_cyclone_console
from backend.core.wallet_core import WalletService
from test_core import TestCoreRunner, formatter, get_console_ui
from backend.data.data_locker import DataLocker
from backend.models.portfolio import PortfolioSnapshot
from backend.core.constants import MOTHER_DB_PATH
from core.logging import log, configure_console_log

wallet_service = WalletService()

ROOT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
PYTHON_EXEC = sys.executable

console = Console()

ICON = {
    "frontend": "🌐",
    "backend": "🛠️",
    "full_stack": "🔄",
    "monitor": "📡",
    "apps": "🧩",
    "verify_db": "🗄️",
    "tests": "🧪",
    "wallet": "💼",
    "cyclone": "🌪️",
    "test_ui": "🧑‍💻",
    "exit": "❌",
}

def banner():
    figlet = Figlet(font="slant")
    console.print(f"[bold cyan]{figlet.renderText('Sonic Launch')}[/bold cyan]")

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def run_background(cmd, cwd):
    system_platform = platform.system()

    if system_platform == "Windows":
        subprocess.Popen(["start", "cmd", "/k"] + cmd, cwd=cwd, shell=True)
    elif system_platform == "Darwin":  # macOS
        subprocess.Popen(["open", "-a", "Terminal.app"] + cmd, cwd=cwd)
    elif system_platform == "Linux":
        subprocess.Popen(["gnome-terminal", "--"] + cmd, cwd=cwd)
    else:
        raise RuntimeError(f"Unsupported OS: {system_platform}")

def wait_and_open(url, secs=3):
    time.sleep(secs)
    webbrowser.open(url)

# Actions
def launch_frontend():
    console.log("🚀 Launching Sonic/Vite frontend...")
    run_background(["npm", "run", "start"], FRONTEND_DIR)
    # Vite's `server.open` option opens the browser automatically
    # wait_and_open("http://localhost:3000")
    console.log("[green]Frontend running at http://localhost:3000[/]")

def launch_backend():
    console.log("🚀 Launching FastAPI backend...")
    run_background([PYTHON_EXEC, "-m", "uvicorn", "sonic_backend_app:app", "--reload", "--port", "5000"], BACKEND_DIR)
    wait_and_open("http://localhost:5000/docs")
    console.log("[green]Backend running at http://localhost:5000[/]")

def launch_full_stack():
    launch_backend()
    launch_frontend()
    console.log("[green]Full stack running in background.[/]")

def launch_sonic_monitor():
    console.log("📡 Launching Sonic Monitor...")
    run_background([PYTHON_EXEC, "sonic_monitor.py"], BACKEND_DIR / "core" / "monitor_core")
    console.log("[green]Sonic Monitor started in background.[/]")

def launch_sonic_apps():
    """Launch backend, frontend and monitor together."""
    launch_backend()
    launch_frontend()
    launch_sonic_monitor()
    console.log("[green]Sonic Apps running with monitor in background.[/]")

def verify_database():
    script = ROOT_DIR / "scripts" / "verify_all_tables_exist.py"
    if script.exists():
        subprocess.call([PYTHON_EXEC, str(script)])
    else:
        console.log("[yellow]verify_all_tables_exist.py not found.[/]")

def run_tests():
    console.log("🚨 Running tests...")
    results = TestCoreRunner().run()
    console.print(formatter.render_summary(results))

def run_test_console():
    TestConsoleUI = get_console_ui()
    TestConsoleUI().start()


def wallet_menu():
    """Simple wallet CRUD interface."""
    while True:
        clear_screen()
        banner()
        console.print("[bold magenta]Wallet Manager[/bold magenta]")
        console.print("1) View wallets")
        console.print("2) Insert Star Wars wallets")
        console.print("3) Delete wallet")
        console.print("4) Delete ALL wallets")
        console.print("0) Back")
        ch = input("→ ").strip()

        if ch == "1":
            wallets = wallet_service.list_wallets()
            if not wallets:
                console.print("[yellow]No wallets found.[/]")
            else:
                for w in wallets:
                    console.print(f"- {w.name} ({w.public_address}) balance={w.balance}")
            input("\nPress ENTER to continue...")
        elif ch == "2":
            count = wallet_service.import_wallets_from_json()
            console.print(f"[green]Imported {count} wallets.[/]")
            input("\nPress ENTER to continue...")
        elif ch == "3":
            name = input("Wallet name to delete: ").strip()
            if name:
                try:
                    wallet_service.delete_wallet(name)
                    console.print(f"[green]Deleted {name}.[/]")
                except Exception as e:
                    console.print(f"[red]Delete failed: {e}[/]")
            input("\nPress ENTER to continue...")
        elif ch == "4":
            confirm = input("Delete ALL wallets? (y/N): ").strip().lower()
            if confirm == "y":
                wallet_service.delete_all_wallets()
                console.print("[green]All wallets deleted.[/]")
            input("\nPress ENTER to continue...")
        elif ch == "0":
            break
        else:
            console.print("[bold red]Invalid selection.[/]")
            input("\nPress ENTER to continue...")


def goals_menu():
    """Manage short term goal information."""
    dl = DataLocker.get_instance()
    mgr = dl.portfolio
    while True:
        clear_screen()
        banner()
        latest = mgr.get_latest_snapshot()
        console.print("[bold magenta]Goals[/bold magenta]")
        console.print("1) Edit goal fields")
        console.print("2) Clear goal")
        console.print("0) Back")
        ch = input("→ ").strip().lower()

        if ch == "1":
            if latest is None:
                console.print("[yellow]No snapshot found. Creating one...[/]")
                mgr.record_snapshot(PortfolioSnapshot())
                latest = mgr.get_latest_snapshot()
            start_time = input(
                f"Session start time [{latest.session_start_time or ''}]: "
            ).strip()
            start_val = input(
                f"Session start value [{latest.session_start_value}]: "
            ).strip()
            curr_val = input(
                f"Current session value [{latest.current_session_value}]: "
            ).strip()
            goal_val = input(
                f"Session goal value [{latest.session_goal_value}]: "
            ).strip()

            fields = {
                "session_start_time": start_time or latest.session_start_time,
                "session_start_value": float(start_val)
                if start_val
                else latest.session_start_value,
                "current_session_value": float(curr_val)
                if curr_val
                else latest.current_session_value,
                "session_goal_value": float(goal_val)
                if goal_val
                else latest.session_goal_value,
            }
            fields["session_performance_value"] = (
                fields["current_session_value"] - fields["session_start_value"]
            )
            mgr.update_entry(latest.id, fields)
            console.print("[green]Goal updated.[/]")
            input("\nPress ENTER to continue...")
        elif ch == "2":
            if latest:
                mgr.update_entry(
                    latest.id,
                    {
                        "session_start_time": None,
                        "session_start_value": 0.0,
                        "current_session_value": 0.0,
                        "session_goal_value": 0.0,
                        "session_performance_value": 0.0,
                    },
                )
                console.print("[green]Goal cleared.[/]")
            else:
                console.print("[yellow]No snapshot found to clear.[/]")
            input("\nPress ENTER to continue...")
        elif ch in {"0", "b"}:
            break
        else:
            console.print("[bold red]Invalid selection.[/]")
            input("\nPress ENTER to continue...")


def operations_menu(db_path: str = str(MOTHER_DB_PATH)):
    """Menu for basic DataLocker operations."""
    locker = DataLocker(db_path)
    while True:
        clear_screen()
        banner()
        console.print("[bold magenta]Operations[/bold magenta]")
        console.print("1) Initialize database")
        console.print("2) Verify database")
        console.print("3) Recover database")
        console.print("b) Back")

        choice = input("→ ").strip().lower()
        if choice == "1":
            locker.initialize_database()
            locker._seed_modifiers_if_empty()
            locker._seed_wallets_if_empty()
            locker._seed_thresholds_if_empty()
            locker._seed_alerts_if_empty()
        elif choice == "2":
            verify_database()
        elif choice == "3":
            locker.db.recover_database()
        elif choice in {"b", "0"}:
            locker.close()
            break
        else:
            console.print("[bold red]Invalid selection.[/]")
        input("")
# Main menu loop
def main():
    while True:
        clear_screen()
        banner()
        menu_body = "\n".join(
            [
                f"1. {ICON['frontend']} Launch [bold]Frontend[/] (Sonic/Vite)",
                f"2. {ICON['backend']} Launch [bold]Backend[/] (FastAPI)",
                f"3. {ICON['full_stack']} Launch [bold]Full Stack[/] (Frontend + Backend)",
                f"4. {ICON['monitor']} Start [bold]Sonic Monitor[/]",
                f"5. {ICON['apps']} Sonic Apps (FastApi + React) w/ Sonic Monitor",
                f"6. {ICON['verify_db']} Verify Database",
                f"7. {ICON['tests']} Run Unit Tests",
                f"8. {ICON['wallet']} Wallet Manager",
                f"9. {ICON['cyclone']} Cyclone Console",
                f"10. {ICON['test_ui']} Test Console UI",
                f"0. {ICON['exit']} Exit",
            ]
        )
        console.print(Panel.fit(menu_body, title="Main Menu", border_style="bright_magenta"))

        choice = input("→ ").strip()

        if choice == "1":
            launch_frontend()
        elif choice == "2":
            launch_backend()
        elif choice == "3":
            launch_full_stack()
        elif choice == "4":
            launch_sonic_monitor()
        elif choice == "5":
            launch_sonic_apps()
        elif choice == "6":
            verify_database()
        elif choice == "7":
            run_tests()
        elif choice == "8":
            wallet_menu()
        elif choice == "9":
            run_cyclone_console()
        elif choice == "10":
            run_test_console()
        elif choice == "11":
            goals_menu()
        elif choice == "0":
            console.print("[bold green]Exiting...[/]")
            break
        else:
            console.print("[bold red]Invalid selection.[/]")

        input("\nPress ENTER to return to menu...")
        clear_screen()

if __name__ == "__main__":
    main()