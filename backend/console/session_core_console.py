from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from backend.data.data_locker import DataLocker
from backend.core.session_core import SessionCore, Session, SessionStatus
from backend.core.wallet_core.wallet_core import WalletCore, WalletConsoleSummary


console = Console()


def _print_header() -> None:
    console.print(
        Panel.fit(
            "[bold magenta]SessionCore Console[/bold magenta]\n[dim]Manage Sonic sessions[/dim]",
            border_style="magenta",
        )
    )


def _session_table(sessions: List[Session]) -> Table:
    table = Table(
        title="📊 Sessions",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
    )
    table.add_column("SID", style="bold cyan")
    table.add_column("Name")
    table.add_column("Primary Wallet")
    table.add_column("Status")
    table.add_column("Created", style="dim")
    table.add_column("Tags", style="dim")

    if not sessions:
        table.add_row("[dim]no sessions[/dim]", "", "", "", "", "")
        return table

    for s in sessions:
        tags_str = ", ".join(s.tags) if isinstance(s.tags, (list, tuple)) else str(s.tags)
        created_str = (
            s.created_at.isoformat(timespec="seconds")
            if isinstance(s.created_at, datetime)
            else str(s.created_at)
        )
        status_value = s.status.value if isinstance(s.status, SessionStatus) else str(s.status)
        status_icon = {
            "active": "🟢",
            "paused": "🟡",
            "closed": "🔴",
        }.get(status_value, "⚪")

        table.add_row(
            s.sid,
            s.name,
            s.primary_wallet_name,
            f"{status_icon} {status_value}",
            created_str,
            tags_str,
        )

    return table


def _pick_wallet(wallet_core: WalletCore) -> Optional[str]:
    wallets: List[WalletConsoleSummary] = wallet_core.list_wallets_for_console()
    if not wallets:
        console.print("[red]No wallets available from WalletCore.[/red]")
        return None

    table = Table(title="🔐 Wallets", box=box.MINIMAL_DOUBLE_HEAD)
    table.add_column("Name", style="bold cyan")
    table.add_column("Public Key")
    table.add_column("Secret")
    table.add_column("Passphrase")

    for w in wallets:
        table.add_row(
            w.wallet_name,
            w.public_key or "[dim]unknown[/dim]",
            "✅" if w.has_secret else "❌",
            "✅" if w.has_passphrase else "❌",
        )

    console.print(table)
    name = Prompt.ask("Primary wallet name (blank to cancel)", default="").strip()
    return name or None


def run_session_core_console(dl: Optional[DataLocker] = None) -> None:
    """
    Entry point for the SessionCore console.

    Called from LaunchPad menu option 16.
    """
    if dl is None:
        try:
            dl = DataLocker.get_instance()  # type: ignore[attr-defined]
        except Exception:
            from backend.core.core_constants import MOTHER_DB_PATH

            dl = DataLocker(str(MOTHER_DB_PATH))

    session_core = SessionCore(dl)
    wallet_core = WalletCore(dl)

    while True:
        console.clear()
        _print_header()

        sessions = session_core.list_sessions()
        console.print(_session_table(sessions))
        console.print()
        console.print(
            "[bold]Commands:[/bold] "
            "[cyan]c[/cyan]=create  "
            "[cyan]a[/cyan]=active only  "
            "[cyan]ra[/cyan]=rename  "
            "[cyan]cl[/cyan]=close  "
            "[cyan]q[/cyan]=quit"
        )

        cmd = Prompt.ask("[magenta]session-core>[/magenta]", default="q").strip().lower()

        if cmd in {"q", "quit", "exit"}:
            break

        if cmd == "a":
            console.clear()
            _print_header()
            active = session_core.list_active_sessions()
            console.print(_session_table(active))
            Prompt.ask("[dim]press Enter to return[/dim]")
            continue

        if cmd == "c":
            wallet_name = _pick_wallet(wallet_core)
            if not wallet_name:
                continue

            default_name = f"{wallet_name}-{datetime.utcnow().date().isoformat()}"
            name = Prompt.ask("Session name", default=default_name).strip()
            goal = Prompt.ask("Goal (optional)", default="").strip()
            tags_raw = Prompt.ask("Tags (comma-separated, optional)", default="").strip()
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else None

            session = session_core.create_session(
                primary_wallet_name=wallet_name,
                name=name,
                goal=goal or None,
                tags=tags or None,
                notes=None,
            )
            console.print(
                f"[green]Created session[/green] [bold]{session.sid}[/bold] "
                f"for wallet [bold]{session.primary_wallet_name}[/bold]."
            )
            Prompt.ask("[dim]press Enter to return[/dim]")
            continue

        if cmd == "ra":
            sid = Prompt.ask("Session ID (sid)").strip()
            new_name = Prompt.ask("New name").strip()
            updated = session_core.rename_session(sid, new_name)
            if not updated:
                console.print(f"[red]No session with sid={sid!r}[/red]")
            else:
                console.print(f"[green]Renamed session[/green] to [bold]{updated.name}[/bold].")
            Prompt.ask("[dim]press Enter to return[/dim]")
            continue

        if cmd == "cl":
            sid = Prompt.ask("Session ID (sid)").strip()
            closed = session_core.close_session(sid)
            if not closed:
                console.print(f"[red]No session with sid={sid!r}[/red]")
            else:
                console.print(f"[yellow]Closed session[/yellow] [bold]{closed.name}[/bold].")
            Prompt.ask("[dim]press Enter to return[/dim]")
            continue

        console.print(f"[yellow]Unknown command: {cmd!r}[/yellow]")
        Prompt.ask("[dim]press Enter to return[/dim]")
