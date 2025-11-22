"""
Drift Core console entrypoint.

Supports two modes:

1) CLI mode (non-interactive):

   python backend/core/drift_core/drift_console.py health
   python backend/core/drift_core/drift_console.py sync-positions
   python backend/core/drift_core/drift_console.py open-long SOL-PERP 25

2) Interactive mode (no arguments):

   # Used by Launch Pad "Launch Drift Console"
   python backend/core/drift_core/drift_console.py

   Presents a small menu for health, sync and simple long orders.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

# ---------------------------------------------------------------------------
# Ensure repo root is on sys.path (match WalletCore / other cores)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Now imports can safely use the backend.* package paths.
from backend.data.data_locker import DataLocker
from backend.core.drift_core.drift_core_service import DriftCoreService

try:
    # Prefer constant if available
    from backend.core.core_constants import MOTHER_DB_PATH as _MOTHER_DB_PATH
except Exception:  # pragma: no cover - best effort
    _MOTHER_DB_PATH = os.getenv("MOTHER_DB_PATH", str(REPO_ROOT / "backend" / "mother.db"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_data_locker() -> DataLocker:
    """
    Obtain a DataLocker instance, preferring the singleton if configured.

    Mirrors patterns elsewhere in the codebase that use DataLocker.get_instance()
    when available, falling back to explicit construction with MOTHER_DB_PATH.
    """
    try:
        if hasattr(DataLocker, "get_instance"):
            return DataLocker.get_instance()  # type: ignore[no-any-return]
    except Exception:
        # fall through to explicit path
        pass

    db_path = os.getenv("MOTHER_DB_PATH", _MOTHER_DB_PATH)
    return DataLocker(db_path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sonic Drift Core console.",
    )

    sub = parser.add_subparsers(
        dest="command",
        # NOTE: do NOT set required=True here; we want interactive mode
        # when no subcommand is provided (Launch Pad).
    )

    sub.add_parser("health", help="Run a basic DriftCore health check.")

    sub.add_parser(
        "sync-positions",
        help="Trigger a Drift positions sync for the primary wallet "
        "(currently stubbed until DriftCore wiring is complete).",
    )

    open_long = sub.add_parser(
        "open-long",
        help="Open a simple long perp position on Drift (symbol + USD size). "
        "Currently routes to DriftCoreService.open_simple_long.",
    )
    open_long.add_argument("symbol", help="Market symbol, e.g. SOL-PERP")
    open_long.add_argument("size_usd", type=float, help="Order size in USD notional")

    return parser


# ---------------------------------------------------------------------------
# Async execution paths
# ---------------------------------------------------------------------------


async def _run_async_cli(args: argparse.Namespace) -> int:
    """
    Handle explicit CLI subcommands (health, sync-positions, open-long).
    """
    dl = _get_data_locker()
    svc = DriftCoreService(dl)

    if args.command == "health":
        payload = await svc.health()
        print("=== DriftCore Health ===")
        for k, v in payload.items():
            print(f"{k}: {v}")
        print()
        return 0

    if args.command == "sync-positions":
        result = await svc.refresh_positions_and_snapshot()
        print("=== Drift Positions Sync ===")
        print(result)
        print()
        return 0

    if args.command == "open-long":
        result = await svc.open_simple_long(args.symbol, args.size_usd)
        print("=== Drift Simple Long ===")
        print(result)
        print()
        return 0

    # Should not happen if parser is wired correctly.
    print(f"[Drift] Unknown command: {args.command}")
    return 1


async def _run_interactive() -> int:
    """
    Interactive console loop used when no subcommand is provided.

    This is what Launch Pad hits when it runs `drift_console.py` with no args.
    """
    dl = _get_data_locker()
    svc = DriftCoreService(dl)

    def _menu() -> None:
        print()
        print("╔════════════════════════ Drift Core Console ════════════════════════╗")
        print("║ 1. Health check                                                    ║")
        print("║ 2. Show Drift balance (total/free)                                 ║")
        print("║ 3. Open simple LONG (symbol + base size)                           ║")
        print("║ 0. Exit                                                             ║")
        print("╚════════════════════════════════════════════════════════════════════╝")
        print()

    while True:
        _menu()
        choice = input("drift> ").strip().lower()

        if choice in ("0", "q", "quit", "exit"):
            print("Exiting Drift Core console.")
            return 0

        if choice == "1":
            payload = await svc.health()
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
                print(f"Error fetching Drift balances: {e}\n")
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
            # Numbered pick list for perp markets
            markets = {
                "1": "BTC-PERP",
                "2": "ETH-PERP",
                "3": "SOL-PERP",
            }

            print("\n  Choose market:")
            print("    1) BTC-PERP")
            print("    2) ETH-PERP")
            print("    3) SOL-PERP")
            market_choice = input("  Market [1-3]: ").strip()

            symbol = markets.get(market_choice)
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
            except NotImplementedError as e:
                print(f"Not implemented yet: {e}")
            except Exception as e:
                import traceback

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
    """
    Entry point for the Drift Core console.

    - If a subcommand is provided (e.g. `health`), run CLI mode.
    - If no subcommand is provided (argv empty / None), run interactive mode.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    # If no subcommand was chosen, drop into interactive mode.
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
