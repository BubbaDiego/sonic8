from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

# Ensure repo root is on sys.path when running as a script
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.data.data_locker import DataLocker

from backend.core.drift_core.drift_core_service import DriftCoreService

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sonic Drift Core console (scaffolding).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health", help="Run a basic DriftCore health check.")

    sub.add_parser(
        "sync-positions",
        help="Trigger a Drift positions sync for the primary wallet "
        "(currently stubbed).",
    )

    open_long = sub.add_parser(
        "open-long",
        help="Open a simple long perp position on Drift (symbol + USD size). "
        "Currently stubbed and will raise NotImplementedError.",
    )
    open_long.add_argument("symbol", help="Market symbol, e.g. SOL-PERP")
    open_long.add_argument("size_usd", type=float, help="Order size in USD notional")

    return parser


def _build_datalocker() -> DataLocker:
    """
    Construct a DataLocker instance using the standard MOTHER_DB_PATH
    convention, falling back to the default backend/mother.db path.

    This mirrors the pattern used elsewhere in Sonic without guessing
    new behavior.
    """
    db_path = os.getenv("MOTHER_DB_PATH", os.path.join("backend", "mother.db"))
    return DataLocker(db_path)


async def _run_async(args: argparse.Namespace) -> int:
    dl = _build_datalocker()
    svc = DriftCoreService(dl)

    if args.command == "health":
        payload = await svc.health()
        print(payload)
        return 0

    if args.command == "sync-positions":
        result = await svc.refresh_positions_and_snapshot()
        print(result)
        return 0

    if args.command == "open-long":
        result = await svc.open_simple_long(args.symbol, args.size_usd)
        print(result)
        return 0

    raise RuntimeError(f"Unhandled command: {args.command}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Entry point for the Drift Core console.

    Example usage (from repo root):

        python -m backend.core.drift_core.drift_console health
    """
    logging.basicConfig(level=logging.INFO)
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return asyncio.run(_run_async(args))
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
