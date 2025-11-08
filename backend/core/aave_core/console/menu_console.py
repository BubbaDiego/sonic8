from __future__ import annotations

import logging
from typing import Optional

from rich.console import Console
from rich.table import Table

from ..aave_config import AaveConfig
from ..aave_service import get_market, get_user_positions, make_portfolio_payload, make_positions_payload
from ..aave_repository import AaveRepository

log = logging.getLogger(__name__)
console = Console()


def _prompt(s: str) -> str:
    return input(s)


def _print_market(cfg: AaveConfig) -> None:
    m = get_market(cfg)
    table = Table(title=f"Aave V3 Market — chain {cfg.chain_id}")
    table.add_column("Symbol", justify="right")
    table.add_column("LTV")
    table.add_column("Liq.Thresh")
    table.add_column("Supply APY")
    table.add_column("Var Borrow APY")
    for r in m.reserves:
        table.add_row(
            r.symbol or "?",
            f"{(r.ltv or 0) :.2f}",
            f"{(r.liquidation_threshold or 0) :.2f}",
            f"{(r.supply_apy or 0) :.4f}",
            f"{(r.variable_borrow_apy or 0) :.4f}",
        )
    console.print(table)


def _print_user(cfg: AaveConfig, user: str) -> None:
    up = get_user_positions(cfg, user)
    # positions
    pos = make_positions_payload(up)
    t = Table(title=f"User Positions — {user}")
    t.add_column("Symbol", justify="right")
    t.add_column("Side")
    t.add_column("Size USD")
    for it in pos["items"]:
        t.add_row(it["symbol"], it["side"], f"{it['sizeUsd']:.2f}")
    console.print(t)
    # health
    h = up.health
    if h:
        console.print(
            f"[bold]Health:[/bold] HF={h.health_factor}  Collateral=${h.total_collateral_usd:.2f}  Debt=${h.total_debt_usd:.2f}"
        )

    # persist snapshots (optional)
    repo = AaveRepository()
    repo.save_positions_snapshot(pos)
    repo.save_portfolio_snapshot(make_portfolio_payload(up))


def run_menu() -> None:
    cfg = AaveConfig.from_env()
    console.print("\n[bold]Aave Console[/bold] — Polygon flavored (set AAVE_CHAIN_ID if needed)\n")
    while True:
        console.print(
            "\n[cyan]1[/cyan] Markets  |  [cyan]2[/cyan] My supplies/borrows  |  [cyan]0[/cyan] Exit"
        )
        choice = _prompt("→ ").strip()
        if choice == "1":
            _print_market(cfg)
        elif choice == "2":
            user = _prompt("  Wallet address (0x…): ").strip()
            _print_user(cfg, user)
        elif choice == "0":
            break
        else:
            console.print("[yellow]Unknown choice[/yellow]")
