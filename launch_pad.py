#!/usr/bin/env python3
"""
🚀 Sonic1 Launch Pad (FastAPI & React/Vite)
Simplified console for debugging the new FastAPI backend and Berry frontend.
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
from backend.console.cyclone_console import run_console
from backend.core.wallet_core import WalletService

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
    console.log("🚀 Launching Berry/Vite frontend...")
    run_background("npm run start", FRONTEND_DIR)
    wait_and_open("http://localhost:3000")  # corrected port to match actual Berry/Vite setup
    console.log("[green]Frontend running at http://localhost:3000[/]")



def launch_backend():
    console.log("🚀 Launching FastAPI backend...")
    run_background(f"{PYTHON_EXEC} -m uvicorn backend.app:app --reload --port 5000", ROOT_DIR)
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
    subprocess.call([PYTHON_EXEC, "-m", "pytest", "-q"])


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


# Main menu loop
def main():
    while True:
        clear_screen()
        banner()
        console.print("1️⃣  Launch [bold]Frontend[/] (Berry/Vite)")
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
            run_console()
        elif choice == "0":
            console.print("[bold green]Exiting...[/]")
            break
        else:
            console.print("[bold red]Invalid selection.[/]")

        input("\nPress ENTER to return to menu...")
        clear_screen()


if __name__ == "__main__":
    main()
