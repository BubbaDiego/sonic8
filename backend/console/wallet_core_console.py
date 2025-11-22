from __future__ import annotations

from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from backend.data.data_locker import DataLocker
from backend.core.wallet_core.wallet_core import (
    WalletCore,
    WalletConsoleSummary,
)


console = Console()


def _print_header() -> None:
    console.print(
        Panel.fit(
            "[bold magenta]WalletCore Console[/bold magenta]\n[dim]Inspect wallets & signers[/dim]",
            border_style="magenta",
        )
    )


def _wallet_table(wallets: list[WalletConsoleSummary]) -> Table:
    table = Table(
        title="🔐 Wallets",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
    )
    table.add_column("Name", style="bold cyan")
    table.add_column("Type", justify="center")
    table.add_column("Public Key", overflow="fold")
    table.add_column("Secret", justify="center")
    table.add_column("Passphrase", justify="center")
    table.add_column("Source", style="dim")

    if not wallets:
        table.add_row("[dim]no wallets configured[/dim]", "", "", "", "", "")
        return table

    for w in wallets:
        table.add_row(
            w.wallet_name,
            w.wallet_type,
            w.public_key or "[dim]unknown[/dim]",
            "✅" if w.has_secret else "❌",
            "✅" if w.has_passphrase else "❌",
            w.source,
        )

    return table


def _show_wallet_detail(core: WalletCore, wallet_name: str) -> None:
    rec = core.get_console_signer_record(wallet_name)
    if rec is None:
        console.print(f"[red]No signer configured for wallet '{wallet_name}'.[/red]")
        return

    table = Table(show_header=False, box=box.MINIMAL)
    table.add_row("Wallet", f"[bold]{rec.wallet_name}[/bold]")
    table.add_row("Public Key", rec.public_key or "[dim]unknown[/dim]")
    table.add_row("Source", rec.source)
    table.add_row("Has Secret", "✅" if rec.secret_base64 else "❌")
    table.add_row("Has Passphrase", "✅" if rec.passphrase else "❌")
    if rec.hint:
        table.add_row("Hint", rec.hint)

    console.print(Panel(table, title="Wallet Detail", border_style="cyan"))


def _reveal_passphrase(core: WalletCore, wallet_name: str) -> None:
    rec = core.get_console_signer_record(wallet_name)
    if rec is None or not rec.passphrase:
        console.print(f"[yellow]No passphrase stored for '{wallet_name}'.[/yellow]")
        return

    confirm = Prompt.ask(
        f"[red]DANGER[/red]: reveal passphrase for [bold]{wallet_name}[/bold]? "
        "Type 'YES' to confirm.",
        default="no",
    )
    if confirm != "YES":
        console.print("[dim]Cancelled.[/dim]")
        return

    console.print(
        Panel(
            f"[bold]{wallet_name}[/bold] passphrase:\n[bright_white]{rec.passphrase}[/bright_white]",
            border_style="red",
        )
    )


def _create_wallet_flow(core: WalletCore) -> None:
    console.print()
    console.print("[bold]Create new wallet[/bold]")

    # Wallet type
    wtype = Prompt.ask(
        "Wallet type [s=signer, v=view]",
        choices=["s", "v"],
        default="s",
    ).lower()
    wallet_type = "signer" if wtype == "s" else "view"

    # Name and public key
    wallet_name = Prompt.ask("Wallet name").strip()
    public_key = Prompt.ask("Public address (Solana pubkey)").strip()

    # Avatar path (optional)
    avatar_path = Prompt.ask(
        "Avatar image path (optional, e.g. frontend/static/images/vader_icon.jpg)",
        default="",
    ).strip()
    if not avatar_path:
        avatar_path = None

    # Notes (optional, for both view & signer)
    notes = Prompt.ask("Notes (optional)", default="").strip()
    if not notes:
        notes = None

    secret_base64: Optional[str] = None
    mnemonic_12: Optional[str] = None
    passphrase: Optional[str] = None

    if wallet_type == "signer":
        # Secret type
        stype = Prompt.ask(
            "Secret type [1=secret_base64, 2=12-word phrase]",
            choices=["1", "2"],
            default="1",
        ).strip()

        if stype == "1":
            secret_base64 = Prompt.ask(
                "Enter secret_base64 (WALLET_SECRET_BASE64-style)"
            ).strip()
        else:
            mnemonic_12 = Prompt.ask(
                "Enter 12-word mnemonic phrase"
            ).strip()

        # Optional UI passphrase
        passphrase_input = Prompt.ask(
            "Wallet UI passphrase (optional)", default=""
        ).strip()
        if passphrase_input:
            passphrase = passphrase_input

    record = core.create_wallet(
        wallet_name=wallet_name,
        public_key=public_key,
        wallet_type=wallet_type,
        avatar_path=avatar_path,
        notes=notes,
        secret_base64=secret_base64,
        mnemonic_12=mnemonic_12,
        passphrase=passphrase,
    )

    console.print()
    console.print(
        f"[green]Created/updated wallet[/green] [bold]{record.wallet_name}[/bold] "
        f"({record.wallet_type})"
    )


def run_wallet_core_console(dl: Optional[DataLocker] = None) -> None:
    """
    Entry point for the WalletCore console.

    If `dl` is not provided, construct DataLocker the same way other
    consoles do (see cyclone_console_service or monitor consoles).
    """
    if dl is None:
        try:
            dl = DataLocker.get_instance()  # type: ignore[attr-defined]
        except Exception:
            from backend.core.core_constants import MOTHER_DB_PATH

            dl = DataLocker(str(MOTHER_DB_PATH))

    core = WalletCore(dl)

    while True:
        console.clear()
        _print_header()

        wallets = core.list_wallets_for_console()
        console.print(_wallet_table(wallets))
        console.print()
        console.print(
            "[bold]Commands:[/bold] "
            "[cyan]c[/cyan]=create wallet  "
            "[cyan]d[/cyan]=detail  "
            "[cyan]p[/cyan]=reveal passphrase  "
            "[cyan]q[/cyan]=quit"
        )

        cmd = Prompt.ask("[magenta]wallet-core>[/magenta]", default="q").strip().lower()

        if cmd in {"q", "quit", "exit"}:
            break

        if cmd.startswith("c"):
            _create_wallet_flow(core)
            Prompt.ask("[dim]press Enter to return[/dim]")
            continue

        if cmd.startswith("d"):
            name = Prompt.ask("Wallet name").strip()
            _show_wallet_detail(core, name)
            Prompt.ask("[dim]press Enter to return[/dim]")
            continue

        if cmd.startswith("p"):
            name = Prompt.ask("Wallet name").strip()
            _reveal_passphrase(core, name)
            Prompt.ask("[dim]press Enter to return[/dim]")
            continue

        console.print(f"[yellow]Unknown command: {cmd!r}[/yellow]")
        Prompt.ask("[dim]press Enter to return[/dim]")
