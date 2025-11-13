from __future__ import annotations

import os
import json
from importlib import import_module
from typing import Any, Dict

from rich.console import Console

console = Console()


def _load_dl():
    """Load a DataLocker instance using the configured database path."""
    try:
        module = import_module("backend.data.data_locker")
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"unable to import DataLocker: {exc}") from exc

    DL = getattr(module, "DataLocker", None)
    if DL is None:
        raise RuntimeError("DataLocker class not found")

    from backend.config.config_loader import load_config

    cfg = load_config()
    db_path = cfg.get("database", {}).get("path")
    if not db_path:
        raise RuntimeError("database.path missing in config")

    if not os.path.isabs(db_path):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        db_path = os.path.join(repo_root, db_path)

    return DL(db_path)


def seed_xcom_providers_from_env(*, console_obj: Console | None = None, dl: Any | None = None) -> None:
    """Populate DL.system['xcom_providers'] from environment variables."""
    printer = console_obj or console

    try:
        locker = dl or _load_dl()
    except Exception as exc:
        printer.print(f"[red]Failed to load DataLocker: {exc}[/red]")
        return

    sysmgr = getattr(locker, "system", None)
    if not sysmgr or not hasattr(sysmgr, "set_var"):
        printer.print("[red]DL.system not available[/red]")
        return

    live = str(os.getenv("SONIC_XCOM_LIVE", "0")).strip().lower() in ("1", "true", "yes", "on")
    sid = os.getenv("TWILIO_SID")
    tok = os.getenv("TWILIO_AUTH_TOKEN")
    frm = os.getenv("TWILIO_FROM")
    to = os.getenv("TWILIO_TO")
    flow = os.getenv("TWILIO_FLOW_SID")

    missing = [k for k, v in [("TWILIO_SID", sid), ("TWILIO_AUTH_TOKEN", tok), ("TWILIO_FROM", frm), ("TWILIO_TO", to)] if not v]
    if missing:
        printer.print(f"[red]Missing env: {', '.join(missing)}[/red]")
        return

    providers: Dict[str, Any] = {
        "voice": {
            "enabled": bool(live),
            "provider": "twilio",
            "account_sid": sid,
            "auth_token": tok,
            "from": frm,
            "to": [to],
        }
    }
    if flow:
        providers["voice"]["flow_sid"] = flow

    sysmgr.set_var("xcom_providers", providers)
    printer.print("[green]xcom_providers saved[/green]")
    try:
        printer.print_json(providers)
    except Exception:
        printer.print(json.dumps(providers, indent=2))


def inspect_xcom_providers(*, console_obj: Console | None = None, dl: Any | None = None) -> None:
    """Inspect the current DL.system['xcom_providers'] value."""
    printer = console_obj or console

    try:
        locker = dl or _load_dl()
    except Exception as exc:
        printer.print(f"[red]Failed to load DataLocker: {exc}[/red]")
        return

    sysmgr = getattr(locker, "system", None)
    prov = sysmgr.get_var("xcom_providers") if sysmgr and hasattr(sysmgr, "get_var") else None
    try:
        printer.print_json(prov or {})
    except Exception:
        printer.print(json.dumps(prov or {}, indent=2))


def run_database_console() -> None:
    """Simple console loop for inspecting and seeding XCom providers."""
    while True:
        console.print("\n[bold cyan]Database Console[/bold cyan]")
        console.print("1) Inspect xcom_providers")
        console.print("2) Seed xcom_providers from ENV (TWILIO_*, SONIC_XCOM_LIVE)")
        console.print("3) Back")
        try:
            choice = input("Select: ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold]Exiting…[/bold]")
            return
        if choice == "1":
            inspect_xcom_providers()
        elif choice == "2":
            seed_xcom_providers_from_env()
        else:
            break


__all__ = [
    "inspect_xcom_providers",
    "run_database_console",
    "seed_xcom_providers_from_env",
]
