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
from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from pyfiglet import Figlet
from backend.core.wallet_core import WalletService
from test_core import TestCoreRunner, formatter, get_console_ui
from backend.data.data_locker import DataLocker
from backend.models.session import Session
from backend.core.core_constants import MOTHER_DB_PATH
from backend.core.logging import log, configure_console_log
from datetime import datetime
from datetime import timedelta
from backend.utils.time_utils import normalize_iso_timestamp

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
    "goals": "🎯",
    "maintenance": "🧹",
    "exit": "❌",
}

def banner():
    figlet = Figlet(font="slant")
    console.print(f"[bold cyan]{figlet.renderText('Sonic Launch')}[/bold cyan]")

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def run_background(cmd, cwd, title: str | None = None):
    """Run a command in a background terminal window.

    Parameters
    ----------
    cmd : list[str]
        Command and arguments to execute.
    cwd : Path | str
        Working directory for the spawned process.
    title : str | None, optional
        Optional descriptive title set via ``CONSOLE_TITLE`` environment
        variable so the child process can identify its origin.
    """

    env = os.environ.copy()
    if title:
        env["CONSOLE_TITLE"] = title

    system_platform = platform.system()

    if system_platform == "Windows":
        subprocess.Popen(["start", "cmd", "/k"] + cmd, cwd=cwd, env=env, shell=True)
    elif system_platform == "Darwin":  # macOS
        subprocess.Popen(["open", "-a", "Terminal.app"] + cmd, cwd=cwd, env=env)
    elif system_platform == "Linux":
        subprocess.Popen(["gnome-terminal", "--"] + cmd, cwd=cwd, env=env)
    else:
        raise RuntimeError(f"Unsupported OS: {system_platform}")

def wait_and_open(url, secs=3):
    time.sleep(secs)
    webbrowser.open(url)

# Actions
def launch_frontend():
    console.log("🚀 Launching Sonic/Vite frontend...")
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        console.log("📦 Installing frontend dependencies (npm install)...")
        try:
            subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, check=False)
        except Exception as exc:
            console.log(f"[yellow]npm install encountered an issue: {exc}[/]")
    fe_cmd = [
        "npm",
        "run",
        "dev",
        "--",
        "--port",
        "3000",
        "--strictPort",
        "--host",
    ]
    run_background(fe_cmd, FRONTEND_DIR, title="Frontend")
    console.log("[green]Frontend starting on http://localhost:3000 (strict)[/]")

def launch_backend():
    console.log("🚀 Launching FastAPI backend...")
    run_background(
        [PYTHON_EXEC, "-m", "uvicorn", "sonic_backend_app:app", "--reload", "--port", "5000"],
        BACKEND_DIR,
        title="Sonic - FastAPI Backend",
    )
    wait_and_open("http://localhost:5000/docs")
    console.log("[green]Backend running at http://localhost:5000[/]")

def launch_full_stack():
    launch_backend()
    launch_frontend()
    console.log("[green]Full stack running in background.[/]")

def launch_sonic_monitor():
    console.log("📡 Launching Sonic Monitor...")
    run_background(
        [PYTHON_EXEC, "sonic_monitor.py"],
        BACKEND_DIR / "core" / "monitor_core",
        title="🦔 Sonic Monitor 🦔",
    )
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


def _display_session(session: Session | None):
    """Show current session details."""
    if not session:
        console.print("[yellow]No session data available.[/]")
    else:
        console.print(f"ID: {session.id}")
        console.print(f"Status: {session.status}")
        console.print(f"Start Time: {session.session_start_time}")
        console.print(f"Start Value: {session.session_start_value}")
        console.print(f"Current Value: {session.current_session_value}")
        console.print(f"Goal Value: {session.session_goal_value}")
        console.print(
            f"Performance: {session.session_performance_value}")
        console.print(f"Notes: {session.notes}")
        console.print(f"Last Modified: {session.last_modified}")


def goals_menu():
    """Manage session and goal information."""
    dl = DataLocker.get_instance()
    mgr = dl.session
    while True:
        clear_screen()
        banner()
        active = mgr.get_active_session()
        console.print(f"[bold magenta]{ICON['goals']} Session / Goals[/bold magenta]")
        console.print("1) View session data")
        console.print("2) Edit session fields")
        console.print("3) Reset session")
        console.print("0) Back")
        ch = input("→ ").strip().lower()

        if ch == "1":
            _display_session(active)
            input("\nPress ENTER to continue...")
        elif ch == "2":
            if active is None:
                console.print("[yellow]No active session. Starting one...[/]")
                active = mgr.start_session()
            start_time_inp = input(
                f"Session start time [{active.session_start_time or ''}]: "
            ).strip()
            start_time = ""
            if start_time_inp:
                normalized = normalize_iso_timestamp(start_time_inp)
                try:
                    datetime.fromisoformat(normalized.replace("Z", "+00:00"))
                    start_time = normalized
                except Exception:
                    console.print("[red]Invalid timestamp format.[/]")
            start_val = input(
                f"Session start value [{active.session_start_value}]: "
            ).strip()
            curr_val = input(
                f"Current session value [{active.current_session_value}]: "
            ).strip()
            goal_val = input(
                f"Session goal value [{active.session_goal_value}]: "
            ).strip()
            perf_val = input(
                f"Session performance value [{active.session_performance_value}]: "
            ).strip()
            status_val = input(
                f"Status [{active.status}]: "
            ).strip()
            notes_val = input(
                f"Notes [{active.notes or ''}]: "
            ).strip()

            if not start_time:
                cur = active.session_start_time
                if isinstance(cur, datetime):
                    start_time = normalize_iso_timestamp(cur.isoformat())
                else:
                    start_time = cur

            fields = {
                "session_start_time": start_time,
                "session_start_value": float(start_val)
                if start_val
                else active.session_start_value,
                "current_session_value": float(curr_val)
                if curr_val
                else active.current_session_value,
                "session_goal_value": float(goal_val)
                if goal_val
                else active.session_goal_value,
            }
            fields["session_performance_value"] = (
                float(perf_val) if perf_val else (
                    fields["current_session_value"] - fields["session_start_value"]
                )
            )
            if status_val:
                fields["status"] = status_val
            if notes_val:
                fields["notes"] = notes_val
            active = mgr.update_session(active.id, fields)
            console.print("[green]Session updated.[/]")
            input("\nPress ENTER to continue...")
        elif ch == "3":
            reset = mgr.reset_session()
            if reset:
                active = reset
                console.print("[green]Session reset.[/]")
            else:
                console.print("[yellow]No active session to reset.[/]")
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


def _run_step(title: str, cmd: list[str], cwd: Path | None = None, soft: bool = False) -> dict:
    """
    Run a subprocess step and capture output.
    soft=True marks a step as non-fatal (warn instead of fail on non-zero rc).
    Returns dict with: title, rc, status, seconds, notes, stdout, stderr
    """
    import time, subprocess

    t0 = time.perf_counter()
    try:
        p = subprocess.run(
            cmd,
            cwd=cwd or ROOT_DIR,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="ignore",
            shell=False,
        )
        rc = p.returncode
        elapsed = time.perf_counter() - t0
        if rc == 0:
            status = "ok"
            notes = "completed"
        else:
            status = "warn" if soft else "fail"
            # Keep a short note line (first 120 chars from stderr/stdout)
            msg = (p.stderr or p.stdout or "error").strip().splitlines()[:1]
            notes = (msg[0] if msg else "error")[:120]
        return {
            "title": title,
            "rc": rc,
            "status": status,
            "seconds": elapsed,
            "notes": notes,
            "stdout": p.stdout,
            "stderr": p.stderr,
            "cmd": cmd,
        }
    except FileNotFoundError as e:
        elapsed = time.perf_counter() - t0
        return {
            "title": title,
            "rc": 127,
            "status": "fail" if not soft else "warn",
            "seconds": elapsed,
            "notes": f"not found: {e}",
            "stdout": "",
            "stderr": str(e),
            "cmd": cmd,
        }


def _format_secs(s: float) -> str:
    # short mm:ss
    return str(timedelta(seconds=int(s)))


def run_daily_maintenance():
    """
    On-demand Daily Maintenance with rich output.
    Steps mirror the 'spec-daily' workflow; prints a emoji summary.
    """

    console.print(Panel.fit("🧹  [bold magenta]On-Demand Daily Maintenance[/]  🧹", border_style="bright_magenta"))
    py = PYTHON_EXEC  # already defined near top
    steps = [
        {
            "title": "Map API routes",
            "cmd": [py, "backend/scripts/spec_api_mapper.py"],
            "soft": False,
        },
        {
            "title": "Draft schemas for unmapped routes",
            "cmd": [py, "backend/scripts/spec_schema_sampler.py"],
            "soft": True,  # sampling may skip if endpoints aren’t up
        },
        {
            "title": "Sweep UI routes/components",
            "cmd": [py, "backend/scripts/ui_sweeper.py"],
            "soft": False,
        },
        {
            "title": "Export OpenAPI",
            "cmd": [py, "backend/scripts/export_openapi.py"],
            "soft": True,  # allow WARN if exporter is noisy in this env
        },
        {
            "title": "Build UI Components doc",
            "cmd": [py, "backend/scripts/build_ui_components_doc.py"],
            "soft": False,
        },
        {
            "title": "Build Schema Bundle (Book + JSON)",
            "cmd": [
                py,
                "backend/scripts/build_schema_bundle.py",
            ]
            + (
                os.getenv("SCHEMA_BUNDLE_PREFIXES", "").split()
                if os.getenv("SCHEMA_BUNDLE_PREFIXES")
                else []
            ),
            "soft": False,
        },
        {
            "title": "Validate ALL specs (backend + UI)",
            "cmd": [py, "backend/scripts/validate_all_specs.py"],
            "soft": False,
        },
    ]

    # Optional screenshot step if UI_BASE_URL is configured
    if os.getenv("UI_BASE_URL"):
        steps.append({
            "title": "UI screenshots (Playwright)",
            "cmd": [py, "backend/scripts/ui_snapshots.py"],
            "soft": True,
        })

    results = []
    for spec in steps:
        res = _run_step(spec["title"], spec["cmd"], cwd=ROOT_DIR, soft=spec.get("soft", False))
        results.append(res)

    # Build a nice table
    table = Table(title="Maintenance Report", show_lines=False, box=None)
    table.add_column("Step", style="bold")
    table.add_column("Status")
    table.add_column("Time")
    table.add_column("Notes", overflow="fold")

    ICONS = {"ok": "✅", "warn": "⚠️", "fail": "❌"}
    c_ok = c_warn = c_fail = 0

    for r in results:
        if r["status"] == "ok":
            c_ok += 1
        elif r["status"] == "warn":
            c_warn += 1
        else:
            c_fail += 1
        table.add_row(
            r["title"],
            f"{ICONS.get(r['status'],'•')} {r['status']}",
            _format_secs(r["seconds"]),
            r["notes"],
        )

    console.print(table)

    # Summary panel
    if c_fail == 0 and c_warn == 0:
        summary_style = "green"
        summary_icon = "🎉"
        headline = "All steps completed successfully."
    elif c_fail == 0:
        summary_style = "yellow"
        summary_icon = "📝"
        headline = "Completed with warnings."
    else:
        summary_style = "red"
        summary_icon = "🚨"
        headline = "Some steps failed."

    console.print(Panel.fit(
        f"{summary_icon}  [bold]{headline}[/]\n"
        f"✅ OK: {c_ok}   ⚠️ WARN: {c_warn}   ❌ FAIL: {c_fail}",
        border_style=summary_style
    ))

    # Offer quick tips for failures
    if c_fail:
        console.print("[bold red]Hints:[/]")
        console.print("- Ensure the FastAPI server is reachable for schema sampling (or ignore if not needed).")
        console.print("- Run missing sweepers locally first if files aren’t generated.")
        console.print("- Check stderr by running the step directly (see commands above).")

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
                f"9. {ICON['test_ui']} Test Console UI",
                f"10. {ICON['goals']} Session / Goals",
                f"11. {ICON['maintenance']} On-Demand Daily Maintenance",
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
            run_test_console()
        elif choice == "10":
            goals_menu()
        elif choice == "11":
            run_daily_maintenance()
        elif choice == "0":
            console.print("[bold green]Exiting...[/]")
            break
        else:
            console.print("[bold red]Invalid selection.[/]")

        input("\nPress ENTER to return to menu...")
        clear_screen()

if __name__ == "__main__":
    main()