#!/usr/bin/env python3
"""
🚀 Sonic1 Launch Pad (FastAPI & React/Vite)
Simplified console for debugging the new FastAPI backend and Sonic frontend.
"""

import subprocess
import webbrowser
import time
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from backend.console.cyclone_console_service import run_cyclone_console
from backend.core.wallet_core import WalletService
from test_core import TestCoreRunner, formatter
from backend.data.data_locker import DataLocker
from backend.core.constants import MOTHER_DB_PATH
from core.logging import log, configure_console_log


wallet_service = WalletService()

ROOT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
PYTHON_EXEC = sys.executable  # Assume venv active, or provide path explicitly

console = Console()


def banner():
    console.print(Panel.fit("[bold cyan]Sonic1 Launch Pad[/bold cyan]"))


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def run_background(cmd, cwd):
    return subprocess.Popen(
        cmd, cwd=cwd, shell=isinstance(cmd, str),
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    )


def wait_and_open(url, secs=3):
    time.sleep(secs)
    webbrowser.open(url)


# Actions
def launch_frontend():
    console.log("🚀 Launching Sonic/Vite frontend...")
    run_background("npm run start", FRONTEND_DIR)
    wait_and_open("http://localhost:3000")  # corrected port to match actual Sonic/Vite setup
    console.log("[green]Frontend running at http://localhost:3000[/]")



def launch_backend():
    console.log("🚀 Launching FastAPI backend...")
    run_background(
        f"{PYTHON_EXEC} -m uvicorn sonic_backend_app:app --reload --port 5000",
        BACKEND_DIR  # explicitly backend directory
    )
    wait_and_open("http://localhost:5000/docs")
    console.log("[green]Backend running at http://localhost:5000[/]")



def launch_full_stack():
    launch_backend()
    launch_frontend()  # frontend now launches correctly on port 3000
    console.log("[green]Full stack running in background.[/]")


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


def launch_sonic_web():
    """Start the Flask dashboard and open the home page."""
    subprocess.Popen([PYTHON_EXEC, "sonic_app.py"])
    log.print_dashboard_link()
    wait_and_open("http://127.0.0.1:5000", secs=1)


def launch_trader_cards():
    """Start the Flask dashboard and open the trader cards route."""
    subprocess.Popen([PYTHON_EXEC, "sonic_app.py"])
    log.print_dashboard_link()
    wait_and_open("http://127.0.0.1:5000/trader/cards", secs=1)


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
        console.print("1️⃣  Launch [bold]Frontend[/] (Sonic/Vite)")
        console.print("2️⃣  Launch [bold]Backend[/] (FastAPI)")
        console.print("3️⃣  Launch [bold]Full Stack[/] (Frontend + Backend)")
        console.print("4️⃣  Verify Database")
        console.print("5️⃣  Run Unit Tests")
        console.print("6️⃣  Wallet Manager")
        console.print("7️⃣  Cyclone Console")
        console.print("0️⃣  Exit")
        choice = input("→ ").strip()

        if choice == "1":
            launch_frontend()
        elif choice == "2":
            launch_backend()
        elif choice == "3":
            launch_full_stack()
        elif choice == "4":
            verify_database()
        elif choice == "5":
            run_tests()
        elif choice == "6":
            wallet_menu()
        elif choice == "7":
            run_cyclone_console()
        elif choice == "0":
            console.print("[bold green]Exiting...[/]")
            break
        else:
            console.print("[bold red]Invalid selection.[/]")

        input("\nPress ENTER to return to menu...")
        clear_screen()


if __name__ == "__main__":
    main()
