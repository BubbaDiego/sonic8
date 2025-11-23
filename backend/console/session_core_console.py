from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from backend.data.data_locker import DataLocker
from backend.core.session_core import SessionCore, Session, SessionPerformance, SessionStatus
from backend.core.wallet_core.wallet_core import WalletCore, WalletConsoleSummary


console = Console()


def _print_header() -> None:
    console.print(
        Panel.fit(
            "[bold magenta]SessionCore Console[/bold magenta]\n[dim]Manage Sonic sessions[/dim]",
            border_style="magenta",
        )
    )


def _session_status_icon(status: SessionStatus) -> str:
    status_value = status.value if isinstance(status, SessionStatus) else str(status)
    return {
        "active": "🟢",
        "paused": "🟡",
        "closed": "🔴",
    }.get(status_value, "⚪")


def _session_table(sessions: List[Session], selected_index: Optional[int]) -> Table:
    table = Table(
        title="📊 Sessions",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
    )
    table.add_column("#", style="dim", justify="right", width=3)
    table.add_column("En", style="dim", width=3)
    table.add_column("SID", style="bold cyan")
    table.add_column("Name")
    table.add_column("Primary Wallet")
    table.add_column("Status")
    table.add_column("Created", style="dim")
    table.add_column("Tags", style="dim")

    if not sessions:
        table.add_row("-", "", "[dim]no sessions[/dim]", "", "", "", "", "")
        return table

    for idx, s in enumerate(sessions, start=1):
        tags_str = ", ".join(s.tags) if isinstance(s.tags, (list, tuple)) else str(s.tags)
        created_str = (
            s.created_at.isoformat(timespec="seconds")
            if isinstance(s.created_at, datetime)
            else str(s.created_at)
        )
        status_icon = _session_status_icon(s.status)
        enabled_icon = "🟢" if s.enabled else "⚪"
        row_prefix = ">" if selected_index is not None and (idx - 1) == selected_index else ""

        table.add_row(
            f"{row_prefix}{idx}",
            enabled_icon,
            s.sid,
            s.name,
            s.primary_wallet_name,
            f"{status_icon} {s.status.value}",
            created_str,
            tags_str,
        )

    return table


def _performance_lines(perf: Optional[SessionPerformance]) -> List[str]:
    if perf is None:
        return ["No equity data found for this session window."]

    def fmt_num(value: Optional[float]) -> str:
        return "—" if value is None else f"{value:,.2f}"

    def fmt_pct(value: Optional[float]) -> str:
        return "—" if value is None else f"{value:+.2f}%"

    return [
        f"Start equity : {fmt_num(perf.start_equity)}",
        f"End equity   : {fmt_num(perf.end_equity)}",
        f"PnL          : {fmt_num(perf.pnl)}",
        f"Return %     : {fmt_pct(perf.return_pct)}",
        f"Max DD %     : {fmt_pct(perf.max_drawdown_pct)}",
    ]


def _session_detail_panel(session: Optional[Session], perf: Optional[SessionPerformance]) -> Panel:
    if session is None:
        body = "No sessions available."
        return Panel(body, title="📈 Selected Session", border_style="green")

    lines = [
        f"[bold]{session.name}[/bold]  ([cyan]{session.sid}[/cyan])",
        f"Wallet: {session.primary_wallet_name}    Status: {session.status.value}    Enabled: {'yes' if session.enabled else 'no'}",
    ]

    if perf is not None:
        window_start = perf.start.isoformat(timespec="seconds")
        window_end = perf.end.isoformat(timespec="seconds")
        samples = perf.samples
    else:
        start_dt = session.created_at if isinstance(session.created_at, datetime) else None
        end_dt = session.closed_at if isinstance(session.closed_at, datetime) else None
        window_start = start_dt.isoformat(timespec="seconds") if start_dt else "—"
        window_end = end_dt.isoformat(timespec="seconds") if end_dt else "—"
        samples = 0

    lines.append(f"Window: {window_start} → {window_end}")
    lines.append(f"Samples: {samples}")
    lines.append("")
    lines.extend(_performance_lines(perf))

    body = "\n".join(lines)
    return Panel(body, title="📈 Selected Session", border_style="green")


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


def _pick_session_by_index(sessions: List[Session], prompt_text: str) -> Optional[Session]:
    """Helper to select a session by its # index."""
    if not sessions:
        console.print("[yellow]No sessions available.[/yellow]")
        return None

    index_str = Prompt.ask(prompt_text, default="").strip()
    if not index_str:
        return None

    if not index_str.isdigit():
        console.print(f"[red]Invalid selection:[/] {index_str!r} (enter a number)")
        return None

    idx = int(index_str)
    if idx < 1 or idx > len(sessions):
        console.print(f"[red]Index out of range.[/] Valid: 1–{len(sessions)}")
        return None

    return sessions[idx - 1]


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

    active_only = False
    enabled_only = False
    selected_index: Optional[int] = 0
    status_message: Optional[str] = None

    while True:
        sessions = session_core.list_sessions(
            active_only=active_only, enabled_only=enabled_only
        )
        if not sessions:
            selected_index = None
        elif selected_index is None:
            selected_index = 0
        else:
            selected_index = max(0, min(selected_index, len(sessions) - 1))

        selected_session = sessions[selected_index] if selected_index is not None else None
        perf = (
            session_core.safe_get_performance(selected_session.sid)
            if selected_session
            else None
        )

        console.clear()
        _print_header()
        if status_message:
            console.print(status_message)
            status_message = None

        console.print(_session_table(sessions, selected_index))
        console.rule(style="dim")
        console.print(_session_detail_panel(selected_session, perf))
        console.print()
        console.print(
            "[bold]Commands:[/bold] "
            "[cyan]c[/cyan]=create  "
            "[cyan]t[/cyan]=toggle enabled  "
            "[cyan]a[/cyan]=active-only  "
            "[cyan]f[/cyan]=enabled-only  "
            "[cyan]v[/cyan]=view/reselect  "
            "[cyan]ra[/cyan]=rename  "
            "[cyan]cl[/cyan]=close  "
            "[cyan]q[/cyan]=quit"
        )

        cmd = Prompt.ask("[magenta]session-core>[/magenta]", default="q").strip().lower()

        if cmd.isdigit():
            idx = int(cmd) - 1
            if 0 <= idx < len(sessions):
                selected_index = idx
            else:
                status_message = f"[yellow]Index out of range. Valid: 1–{len(sessions)}[/yellow]"
            continue

        if cmd in {"q", "quit", "exit"}:
            break

        if cmd == "a":
            active_only = not active_only
            continue

        if cmd == "f":
            enabled_only = not enabled_only
            continue

        if cmd == "c":
            wallet_name = _pick_wallet(wallet_core)
            if not wallet_name:
                status_message = "[red]No wallet selected.[/red]"
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
                notes="",
            )
            status_message = (
                f"[green]Created session[/green] [bold]{session.sid}[/bold] "
                f"for wallet [bold]{session.primary_wallet_name}[/bold]."
            )
            sessions = session_core.list_sessions(
                active_only=active_only, enabled_only=enabled_only
            )
            for idx, sess in enumerate(sessions):
                if sess.sid == session.sid:
                    selected_index = idx
                    break
            continue

        if cmd == "t":
            if selected_session is None:
                status_message = "[yellow]No session selected to toggle.[/yellow]"
                continue
            updated = session_core.set_session_enabled(
                selected_session.sid, not selected_session.enabled
            )
            if updated:
                status_message = (
                    f"[cyan]Session[/cyan] {updated.sid} set to "
                    f"{'enabled' if updated.enabled else 'disabled'}."
                )
            else:
                status_message = "[red]Failed to update session state.[/red]"
            continue

        if cmd == "v":
            if not sessions:
                status_message = "[yellow]No sessions to select.[/yellow]"
                continue
            chosen = _pick_session_by_index(
                sessions, "Select session # (blank to cancel)"
            )
            if chosen:
                selected_index = sessions.index(chosen)
            continue

        if cmd == "ra":
            if not sessions:
                status_message = "[yellow]No sessions to rename.[/yellow]"
                continue
            chosen = _pick_session_by_index(
                sessions, "Select session # to rename (blank for selected)"
            )
            if chosen is None and selected_session is not None:
                chosen = selected_session
            if not chosen:
                continue

            new_name = Prompt.ask("New name", default=chosen.name).strip()
            if not new_name:
                status_message = "[yellow]Name unchanged.[/yellow]"
                continue

            updated = session_core.rename_session(chosen.sid, new_name)
            if not updated:
                status_message = f"[red]No session with sid={chosen.sid!r}[/red]"
            else:
                status_message = (
                    f"[green]Renamed session[/green] to [bold]{updated.name}[/bold]."
                )
                for idx, sess in enumerate(sessions):
                    if sess.sid == updated.sid:
                        selected_index = idx
                        break
            continue

        if cmd == "cl":
            if not sessions:
                status_message = "[yellow]No sessions to close.[/yellow]"
                continue
            chosen = _pick_session_by_index(
                sessions, "Select session # to close (blank for selected)"
            )
            if chosen is None:
                chosen = selected_session
            if not chosen:
                continue

            confirm = Prompt.ask(
                f"Type [bold]YES[/bold] to close session [cyan]{chosen.sid}[/cyan] ({chosen.name})",
                default="no",
            ).strip()
            if confirm != "YES":
                status_message = "[dim]Cancelled.[/dim]"
                continue

            closed = session_core.close_session(chosen.sid)
            if not closed:
                status_message = f"[red]No session with sid={chosen.sid!r}[/red]"
            else:
                status_message = f"[yellow]Closed session[/yellow] [bold]{closed.name}[/bold]."
            continue

        status_message = f"[yellow]Unknown command: {cmd!r}[/yellow]"
