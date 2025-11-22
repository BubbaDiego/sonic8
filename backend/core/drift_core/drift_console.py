"""
Drift Core console entrypoint.

Interactive menu for:
- Health check
- Drift balance (total/free collateral)
- Simple LONG order on BTC/ETH/SOL perps
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import traceback
from pathlib import Path
from typing import Optional, Sequence

# ---------------------------------------------------------------------------
# Ensure repo root is on sys.path
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.data.data_locker import DataLocker
from backend.core.drift_core.drift_core_service import DriftCoreService

try:
    from backend.core.logging import console  # Sonic-wide rich Console
    HAVE_RICH_CONSOLE = True
except Exception:
    console = None
    HAVE_RICH_CONSOLE = False


def _get_data_locker() -> DataLocker:
    try:
        if hasattr(DataLocker, "get_instance"):
            return DataLocker.get_instance()  # type: ignore[no-any-return]
    except Exception:
        pass

    db_path = os.getenv("MOTHER_DB_PATH", str(REPO_ROOT / "backend" / "mother.db"))
    return DataLocker(db_path)


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sonic Drift Core console.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("health", help="Run a basic DriftCore health check.")
    sub.add_parser("balance", help="Show Drift balance summary (total/free).")

    open_long = sub.add_parser(
        "open-long",
        help="Open a simple long perp position on Drift (symbol + base size).",
    )
    open_long.add_argument("symbol", help="Market symbol, e.g. SOL-PERP")
    open_long.add_argument("size_base", type=float, help="Order size in base units, e.g. 0.1 SOL")

    return parser


# ---------------------------------------------------------------------------
# Pretty UI helpers
# ---------------------------------------------------------------------------


def _print_header() -> None:
    title = " Drift Core Console "
    border = "═" * (len(title) + 2)
    line = f"╔{border}╗\n║ {title} ║\n╚{border}╝"
    if HAVE_RICH_CONSOLE and console is not None:
        console.print(f"[bold cyan]{line}[/bold cyan]")
    else:
        print(line)


def _print_menu() -> None:
    _print_header()
    body = [
        "  1. 🩺  Health check",
        "  2. 💰  Show Drift balance (total/free)",
        "  3. 📈  Open simple LONG (symbol + base size)",
        "  0. ⏻  Exit",
    ]
    if HAVE_RICH_CONSOLE and console is not None:
        from rich.panel import Panel

        panel = Panel.fit(
            "\n".join(body),
            title="Options",
            border_style="bright_magenta",
        )
        console.print(panel)
    else:
        print("\n".join(body))
    print()


# ---------------------------------------------------------------------------
# Async operations
# ---------------------------------------------------------------------------


async def _run_async_cli(args: argparse.Namespace) -> int:
    dl = _get_data_locker()
    svc = DriftCoreService(dl)

    if args.command == "health":
        payload = await svc.health()
        print("=== DriftCore Health ===")
        for k, v in payload.items():
            print(f"{k}: {v}")
        print()
        return 0

    if args.command == "balance":
        summary = await svc.get_balance()
        print("=== Drift Balance Summary ===")
        for k, v in summary.items():
            print(f"{k}: {v}")
        print()
        return 0

    if args.command == "open-long":
        result = await svc.open_simple_long(args.symbol, args.size_base)
        print("=== Drift Simple Long ===")
        print(result)
        print()
        return 0

    print(f"Unknown command: {args.command}")
    return 1


async def _run_interactive() -> int:
    dl = _get_data_locker()
    svc = DriftCoreService(dl)

    while True:
        _print_menu()
        choice = input("drift> ").strip().lower()

        if choice in ("0", "q", "quit", "exit"):
            print("Exiting Drift Core console.")
            return 0

        if choice == "1":
            try:
                payload = await svc.health()
            except Exception as e:
                print(f"\n[Drift] Health check failed: {repr(e)}")
                traceback.print_exc()
                print()
                continue

            print("\n=== DriftCore Health ===")
            for k, v in payload.items():
                print(f"{k}: {v}")
            print()
            continue

        if choice == "2":
            print("\n[Drift] Fetching Drift balances...")
            try:
                summary = await svc.get_balance()
            except Exception as e:
                print(f"\n[Drift] Error fetching Drift balances: {repr(e)}")
                print("------ full traceback ------")
                traceback.print_exc()
                print("------ end traceback -------\n")
                continue

            owner = summary.get("owner")
            total_q = summary.get("total_collateral_quote")
            free_q = summary.get("free_collateral_quote")
            total_ui = summary.get("total_collateral_ui")
            free_ui = summary.get("free_collateral_ui")

            print("\n=== Drift Balance Summary ===")
            if owner:
                print(f"Owner:                {owner}")
            print(f"Total collateral (raw):   {total_q}")
            print(f"Free collateral (raw):    {free_q}")
            try:
                print(f"Total collateral (UI):    {float(total_ui):.4f}")
                print(f"Free collateral (UI):     {float(free_ui):.4f}")
            except Exception:
                print(f"Total collateral (UI):    {total_ui}")
                print(f"Free collateral (UI):     {free_ui}")
            print()
            continue

        if choice == "3":
            markets = {
                "1": "BTC-PERP",
                "2": "ETH-PERP",
                "3": "SOL-PERP",
            }

            print("\n  Choose market:")
            print("    1) BTC-PERP")
            print("    2) ETH-PERP")
            print("    3) SOL-PERP")
            m_choice = input("  Market [1-3]: ").strip()
            symbol = markets.get(m_choice)
            if symbol is None:
                print("  Invalid market selection. Please choose 1, 2, or 3.\n")
                continue

            size_raw = input("  Size (base units, e.g. 0.1 SOL): ").strip()
            try:
                size_base = float(size_raw)
            except ValueError:
                print("  Invalid size; please enter a numeric value.\n")
                continue

            print(f"\n[Drift] Opening LONG {symbol} size {size_base} (base units)...")
            try:
                result = await svc.open_simple_long(symbol, size_base)
                print("=== Drift Simple Long ===")
                print(result)
            except Exception as e:
                print(f"Error placing Drift order: {repr(e)}")
                print("------ full traceback ------")
                traceback.print_exc()
                print("------ end traceback -------")
            print()
            continue

        print("Unrecognized selection. Please choose 0–3.\n")


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "command", None) is None:
        try:
            return asyncio.run(_run_interactive())
        except KeyboardInterrupt:
            print("\nInterrupted by user.")
            return 130

    try:
        return asyncio.run(_run_async_cli(args))
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
