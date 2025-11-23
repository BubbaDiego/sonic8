from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from backend.data.data_locker import DataLocker
from backend.core.session_core import SessionCore
from backend.core.wallet_core.wallet_core import WalletCore, WalletConsoleSummary


console = Console()


@dataclass
class _SessionRow:
    index: int
    session: object  # Session
    performance: object | None  # SessionPerformance or None


def _print_header() -> None:
    console.print(
        Panel.fit(
            "[bold magenta]SessionCore Console[/bold magenta]\n[dim]Manage Sonic sessions[/dim]",
            border_style="magenta",
        )
    )


def _build_rows(session_core: SessionCore) -> List[_SessionRow]:
    sessions = session_core.list_sessions()
    rows: List[_SessionRow] = []
    for idx, s in enumerate(sessions, start=1):
        perf = None
        # Try to compute performance, but never crash the console if it fails.
        try:
            perf = session_core.get_session_performance(getattr(s, "sid", getattr(s, "id", "")))
        except Exception:
            # Swallow errors here; they will show up as "N/A" in the table.
            perf = None
        rows.append(_SessionRow(index=idx, session=s, performance=perf))
    return rows


def _render_table(rows: List[_SessionRow]) -> None:
    table = Table(
        title="📊 Sessions",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
    )
    table.add_column("#", justify="right", style="dim")
    table.add_column("SID", style="bold cyan")
    table.add_column("Name")
    table.add_column("Primary Wallet")
    table.add_column("Status")
    table.add_column("P&L (USD)", justify="right")
    table.add_column("Return %", justify="right")

    if not rows:
        table.add_row("[dim]–[/dim]", "", "[dim]no sessions[/dim]", "", "", "", "")
        console.print(table)
        return

    for row in rows:
        s = row.session
        perf = row.performance

        sid = getattr(s, "sid", getattr(s, "id", ""))
        name = getattr(s, "name", "")
        wallet = getattr(s, "primary_wallet_name", getattr(s, "wallet_name", ""))
        status = getattr(s, "status", "")

        pnl_str = "—"
        ret_str = "—"

        if perf is not None:
            pnl = getattr(perf, "pnl_usd", None)
            ret = getattr(perf, "return_pct", None)

            if pnl is not None:
                sign = "+" if pnl >= 0 else ""
                pnl_str = f"{sign}{pnl:,.2f}"
                if pnl > 0:
                    pnl_str = f"[green]{pnl_str}[/green]"
                elif pnl < 0:
                    pnl_str = f"[red]{pnl_str}[/red]"

            if ret is not None:
                sign = "+" if ret >= 0 else ""
                ret_str = f"{sign}{ret:.2f}%"

        table.add_row(
            str(row.index),
            str(sid),
            str(name),
            str(wallet),
            str(status),
            pnl_str,
            ret_str,
        )

    console.print(table)


def _select_row(rows: List[_SessionRow], prompt_text: str) -> Optional[_SessionRow]:
    if not rows:
        console.print("[yellow]No sessions available.[/yellow]")
        return None

    choice = Prompt.ask(prompt_text, default="").strip()
    if not choice:
        return None

    try:
        idx = int(choice)
    except ValueError:
        console.print(f"[red]Invalid index: {choice!r}[/red]")
        return None

    if idx < 1 or idx > len(rows):
        console.print(f"[red]Index out of range. Valid range is 1–{len(rows)}.[/red]")
        return None

    return rows[idx - 1]


def _performance_panel(row: _SessionRow) -> Panel:
    s = row.session
    perf = row.performance

    sid = getattr(s, "sid", getattr(s, "id", ""))
    name = getattr(s, "name", "")
    wallet = getattr(s, "primary_wallet_name", getattr(s, "wallet_name", ""))
    status = getattr(s, "status", "")

    lines: List[str] = []
    lines.append(f"[bold]{name}[/bold]  ([cyan]{sid}[/cyan])")
    lines.append(f"[dim]Wallet[/dim]: {wallet}")
    lines.append(f"[dim]Status[/dim]: {status}")
    lines.append("")

    if perf is None:
        lines.append("[yellow]No performance data available for this session.[/yellow]")
    else:
        start_eq = getattr(perf, "start_equity_usd", None)
        start_ts = getattr(perf, "start_equity_ts", None)
        curr_eq = getattr(perf, "current_equity_usd", None)
        curr_ts = getattr(perf, "current_equity_ts", None)
        pnl = getattr(perf, "pnl_usd", None)
        ret = getattr(perf, "return_pct", None)

        def _fmt(v: Optional[float]) -> str:
            return f"{v:,.2f}" if isinstance(v, (int, float)) else "N/A"

        def _fmt_ts(ts) -> str:
            return ts.isoformat(timespec="seconds") if hasattr(ts, "isoformat") else "N/A"

        lines.append(f"[dim]Start equity[/dim]:   {_fmt(start_eq)}  [dim]@[/dim] {_fmt_ts(start_ts)}")
        lines.append(f"[dim]Current equity[/dim]: {_fmt(curr_eq)}  [dim]@[/dim] {_fmt_ts(curr_ts)}")

        lines.append("")

        if pnl is None:
            lines.append("[dim]PnL[/dim]:         N/A")
        else:
            sign = "+" if pnl >= 0 else ""
            base = f"{sign}{pnl:,.2f}"
            if pnl > 0:
                base = f"[green]{base}[/green]"
            elif pnl < 0:
                base = f"[red]{base}[/red]"
            lines.append(f"[dim]PnL[/dim]:         {base}")

        if ret is None:
            lines.append("[dim]Return[/dim]:      N/A")
        else:
            sign = "+" if ret >= 0 else ""
            lines.append(f"[dim]Return[/dim]:      {sign}{ret:.2f}%")

    body = "\n".join(lines)
    return Panel(body, title="📈 Session Performance", border_style="green")


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
    Interactive SessionCore console.

    This function is called from Launch Pad (Session / Goals).
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

        rows = _build_rows(session_core)
        _render_table(rows)
        console.print()
        console.print(
            "[bold]Commands:[/bold] "
            "[cyan]c[/cyan]=create  "
            "[cyan]a[/cyan]=active only (view)  "
            "[cyan]v[/cyan]=view performance  "
            "[cyan]ra[/cyan]=rename  "
            "[cyan]cl[/cyan]=close  "
            "[cyan]q[/cyan]=quit"
        )

        cmd = Prompt.ask("[magenta]session-core>[/magenta]", default="q").strip().lower()

        if cmd in {"q", "quit", "exit"}:
            return

        if cmd == "v":
            row = _select_row(rows, "Select session # (blank to cancel)")
            if not row:
                continue

            try:
                perf = session_core.get_session_performance(
                    getattr(row.session, "sid", getattr(row.session, "id", ""))
                )
                row.performance = perf
                console.clear()
                _print_header()
                console.print(_performance_panel(row))
            except Exception as exc:
                console.clear()
                _print_header()
                console.print(
                    Panel(
                        f"[red]Error computing performance:[/red] {exc!r}",
                        border_style="red",
                        title="Performance error",
                    )
                )

            Prompt.ask("[dim]press Enter to return[/dim]")
            continue

        if cmd == "ra":
            row = _select_row(rows, "Select session # to rename (blank to cancel)")
            if not row:
                continue
            new_name = Prompt.ask("New session name", default=getattr(row.session, "name", "")).strip()
            if not new_name:
                continue
            try:
                sid = getattr(row.session, "sid", getattr(row.session, "id", ""))
                session_core.rename_session(sid, new_name)
            except Exception as exc:
                console.print(f"[red]Error renaming session:[/red] {exc!r}")
                Prompt.ask("[dim]press Enter to return[/dim]")
                continue
            continue

        if cmd == "cl":
            row = _select_row(rows, "Select session # to close (blank to cancel)")
            if not row:
                continue
            try:
                sid = getattr(row.session, "sid", getattr(row.session, "id", ""))
                session_core.close_session(sid)
            except Exception as exc:
                console.print(f"[red]Error closing session:[/red] {exc!r}")
                Prompt.ask("[dim]press Enter to return[/dim]")
                continue
            continue

        if cmd == "c":
            wallet_name = _pick_wallet(wallet_core)
            if not wallet_name:
                continue

            name = Prompt.ask("Session name", default="").strip()
            if not name:
                continue
            goal = Prompt.ask("Goal (optional)", default="").strip() or None
            tags_raw = Prompt.ask("Tags (comma-separated, optional)", default="").strip()
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else None
            notes = Prompt.ask("Notes (optional)", default="").strip() or None

            try:
                session_core.create_session(
                    primary_wallet_name=wallet_name,
                    name=name,
                    goal=goal,
                    tags=tags,
                    notes=notes,
                )
            except Exception as exc:
                console.print(f"[red]Error creating session:[/red] {exc!r}")
                Prompt.ask("[dim]press Enter to return[/dim]")
                continue
            continue

        if cmd == "a":
            active_rows = [r for r in rows if str(getattr(r.session, "status", "")).lower() == "active"]
            console.clear()
            _print_header()
            _render_table(active_rows)
            Prompt.ask("[dim]press Enter to return[/dim]")
            continue

        console.print(f"[yellow]Unknown command: {cmd!r}[/yellow]")
        Prompt.ask("[dim]press Enter to return[/dim]")
