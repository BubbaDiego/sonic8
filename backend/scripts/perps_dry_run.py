from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass

from backend.services.perps.positions_request import (
    dry_run_open_position_request,
    load_signer,
)


def _print_line(ch: str = "─", width: int = 88) -> None:
    print(ch * width)


def _pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, default=str)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="perps_dry_run",
        description="Dry-run a Jupiter Perps increase-position request and print a step-by-step report.",
    )
    parser.add_argument(
        "--market",
        default=os.getenv("PERPS_MARKET", "SOL-PERP"),
        help="Market symbol (e.g. SOL-PERP)",
    )
    parser.add_argument(
        "--side",
        default=os.getenv("PERPS_SIDE", "long"),
        choices=["long", "short"],
        help="Trade side",
    )
    parser.add_argument(
        "--size-usd",
        type=float,
        default=float(os.getenv("PERPS_SIZE_USD", "11")),
        help="Position size in USD (notional)",
    )
    parser.add_argument(
        "--collateral-usd",
        type=float,
        default=float(os.getenv("PERPS_COLLATERAL_USD", "11")),
        help="Collateral to post in USD",
    )
    parser.add_argument(
        "--logs",
        type=int,
        default=int(os.getenv("PERPS_LOG_LINES", "20")),
        help="How many log lines per step to print",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full dry-run response as JSON (in addition to the summary)",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    wallet = load_signer()

    try:
        report: Dict[str, Any] = dry_run_open_position_request(
            wallet,
            market=args.market,
            side=args.side,
            size_usd=args.size_usd,
            collateral_usd=args.collateral_usd,
        )
    except TypeError:
        report = dry_run_open_position_request(
            wallet,
            args.market,
            args.side,
            args.size_usd,
            args.collateral_usd,
        )

    ok = bool(report.get("ok"))
    instruction = report.get("instruction")
    position = report.get("position")
    position_request = report.get("positionRequest")
    position_request_ata = report.get("positionRequestAta")
    final_mapping = report.get("finalMapping", {})

    _print_line("═")
    print("Jupiter Perps · Dry-run (increase position)")
    _print_line("═")

    print(f"Result        : {'OK' if ok else 'FAILED'}")
    print(f"Instruction   : {instruction}")
    print(f"Market/Side   : {args.market} / {args.side.upper()}")
    print(f"Size USD      : {args.size_usd}")
    print(f"Collateral USD: {args.collateral_usd}")
    print(f"Position      : {position}")
    print(f"Request       : {position_request}")
    print(f"Request ATA   : {position_request_ata}")

    _print_line()
    print("Final account mapping (normalized):")
    print(_pretty(final_mapping))

    steps = report.get("steps") or []
    if steps:
        _print_line()
        print("Simulation steps")
        _print_line()
        for idx, step in enumerate(steps, 1):
            label = step.get("label")
            step_ok = step.get("ok")
            err_code = step.get("errorCode")
            err_msg = step.get("errorMessage")
            right_hint = (
                step.get("rightPdaHint")
                or step.get("rightPda")
                or step.get("unknownAccount")
            )
            print(f"[{idx:02d}] {label} :: {'OK' if step_ok else 'FAILED'}")
            if err_code or err_msg:
                print(f"     Error   : {err_code} - {err_msg}")
            if right_hint:
                print(f"     Hint    : {right_hint}")
            logs = step.get("logs") or []
            if logs:
                print("     Logs    :")
                for line in logs[: max(0, args.logs)]:
                    print("       ", line)
            _print_line()

    if args.json:
        _print_line()
        print("RAW REPORT JSON")
        _print_line()
        print(_pretty(report))

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
