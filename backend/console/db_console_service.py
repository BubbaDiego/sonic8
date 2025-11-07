# backend/console/db_console_service.py
from __future__ import annotations

import os
import sqlite3
import json
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, IntPrompt, Confirm

# Optional: DataLocker (DL) is used when available for convenience actions
try:
    from backend.data.data_locker import DataLocker  # type: ignore
except Exception:  # pragma: no cover
    DataLocker = None  # type: ignore


ICON: Dict[str, str] = {
    "db": "🗄️",
    "table": "📚",
    "schema": "🧬",
    "rows": "👁️",
    "search": "🔎",
    "relations": "🧩",
    "dl": "🧰",
    "sysvars": "🧷",
    "wallets": "👝",
    "maint": "🛠️",
    "integrity": "🧪",
    "fk": "🔗",
    "wal": "🧱",
    "vacuum": "🧹",
    "analyze": "📊",
    "reindex": "🧮",
    "wizard": "🧙",
    "backup": "📸",
    "restore": "♻️",
    "export": "📤",
    "import": "📥",
    "query": "⌨️",
    "audit": "📜",
    "heavy": "🏋️",
    "lock": "🔐",
    "settings": "⚙️",
    "help": "❓",
    "ok": "✅",
    "warn": "⚠️",
    "err": "❌",
    "info": "ℹ️",
    "back": "↩️",
}

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DB_CONSOLE_ENV = "DB_CONSOLE_DB"  # optional override
DEFAULT_DB = os.path.join(REPO_ROOT, "backend", "mother.db")
BACKUP_DIR = os.path.join(REPO_ROOT, "reports", "db_backups")
EXPORT_DIR = os.path.join(REPO_ROOT, "reports", "db_console")
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)


@dataclass
class ConsoleState:
    danger_mode: bool = False
    page_size: int = 200


class DbConsoleService:
    """
    Sonic Database Console (SQLite) — exploration + maintenance with guardrails.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.console = Console()
        self.state = ConsoleState()
        self.db_path = db_path or self._detect_db_path()

    # ----------------- entry -----------------

    def run_console(self) -> None:
        while True:
            self._clear()
            self._render_header()
            menu = Table.grid(padding=(0, 2))
            for label in (
                f"1) {ICON['table']} Explore",
                f"2) {ICON['dl']} DataLocker Hub",
                f"3) {ICON['maint']} Maintenance",
                f"4) {ICON['wizard']} Wizards",
                f"5) {ICON['backup']} Backup / {ICON['restore']} Restore / {ICON['export']} Export",
                f"6) {ICON['query']} Query Runner (read-only)",
                f"7) {ICON['audit']} Diagnostics",
                f"8) {ICON['settings']} Settings",
                f"9) {ICON['help']} Help",
                f"0) {ICON['back']} Exit",
            ):
                menu.add_row(label)
            self.console.print(Panel(menu, title=f"{ICON['db']} DB Console — Main Menu", border_style="cyan"))

            ch = Prompt.ask("Select")
            if ch == "1":
                self._screen_explore()
            elif ch == "2":
                self._screen_dlocker()
            elif ch == "3":
                self._screen_maintenance()
            elif ch == "4":
                self._screen_wizards()
            elif ch == "5":
                self._screen_backup_restore_export()
            elif ch == "6":
                self._screen_query_runner()
            elif ch == "7":
                self._screen_diagnostics()
            elif ch == "8":
                self._screen_settings()
            elif ch == "9":
                self._screen_help()
            elif ch in {"0", "q", "Q", "quit", "exit"}:
                self.console.print("\nbye 👋\n"); return
            else:
                self.console.print(f"{ICON['warn']} Invalid selection."); self._pause()

    # ----------------- header -----------------

    def _render_header(self) -> None:
        size = self._file_size(self.db_path)
        journal = self._get_pragma("journal_mode")
        fks = self._get_pragma("foreign_keys")
        pages = self._db_pages()
        hdr = Text.assemble(
            (f" {ICON['db']} {self.db_path}  ", "bold white"),
            (f"| 📦 {size}  ", "cyan"),
            (f"| 📄 {pages} pages  ", "magenta"),
            (f"| {ICON['wal']} {journal.upper() if isinstance(journal,str) else journal}  ", "yellow"),
            (f"| {ICON['fk']} {'ON' if fks else 'OFF'}  ", "green" if fks else "red"),
        )
        self.console.print(Panel(hdr, border_style="cyan"))

    # ----------------- screens -----------------

    def _screen_explore(self) -> None:
        while True:
            self._clear(); self._render_header()
            self.console.print(f"{ICON['table']} [bold]Explore[/]\n")
            self.console.print("1) List tables/views")
            self.console.print("2) Show schema (pick from list)")
            self.console.print("3) View rows (pick from list)")
            self.console.print("0) Back\n")
            ch = Prompt.ask("Select", default="1")
            if ch == "1":
                self._list_tables()
            elif ch == "2":
                name = self._pick_table(title="Pick a table/view for schema")
                if name: self._show_schema(name)
            elif ch == "3":
                name = self._pick_table(title="Pick a table/view to browse rows")
                if name: self._view_rows_paged(name)
            elif ch == "0":
                return
            self._pause()

    def _screen_dlocker(self) -> None:
        self._clear(); self._render_header()
        self.console.print(f"{ICON['dl']} [bold]DataLocker Hub[/] (best-effort; only if DL available)\n")
        self.console.print(f"1) {ICON['sysvars']} View / Edit system vars")
        self.console.print(f"2) {ICON['wallets']} Wallets (list/toggle)")
        self.console.print("0) Back\n")
        ch = Prompt.ask("Select", default="1")
        if ch == "1":
            self._dl_system_vars()
        elif ch == "2":
            self._dl_wallets()
        self._pause()

    def _screen_maintenance(self) -> None:
        self._clear(); self._render_header()
        self.console.print(f"{ICON['maint']} [bold]Maintenance[/]\n")
        self.console.print(f"1) {ICON['integrity']} PRAGMA integrity_check")
        self.console.print(f"2) {ICON['integrity']} PRAGMA quick_check")
        self.console.print(f"3) {ICON['fk']} PRAGMA foreign_key_check")
        self.console.print(f"4) Toggle {ICON['fk']} foreign_keys (ON/OFF)")
        self.console.print(f"5) Toggle {ICON['wal']} journal_mode (WAL/DELETE)")
        self.console.print(f"6) {ICON['vacuum']} VACUUM")
        self.console.print(f"7) {ICON['analyze']} ANALYZE")
        self.console.print(f"8) {ICON['reindex']} REINDEX")
        self.console.print("0) Back\n")
        ch = Prompt.ask("Select", default="1")
        if ch == "1":
            self._pragma_check("integrity_check")
        elif ch == "2":
            self._pragma_check("quick_check")
        elif ch == "3":
            self._fk_check()
        elif ch == "4":
            self._toggle_foreign_keys()
        elif ch == "5":
            self._toggle_wal()
        elif ch == "6":
            self._vacuum()
        elif ch == "7":
            self._analyze()
        elif ch == "8":
            self._reindex()
        self._pause()

    def _screen_wizards(self) -> None:
        self._clear(); self._render_header()
        self.console.print(f"{ICON['wizard']} [bold]Wizards[/]\n")
        self.console.print("1) Normalize liquid monitor keys (asset_thresholds → thresholds)")
        self.console.print("2) Reseed configs (alerts/liquid/price) if missing")
        self.console.print("3) Cleanse Alerts (DL)")
        self.console.print("0) Back\n")
        ch = Prompt.ask("Select", default="1")
        if ch == "1":
            self._wiz_normalize_liquid_keys()
        elif ch == "2":
            self._wiz_reseed_configs()
        elif ch == "3":
            self._wiz_cleanse_alerts()
        self._pause()

    def _screen_backup_restore_export(self) -> None:
        self._clear(); self._render_header()
        self.console.print(f"{ICON['backup']} [bold]Backup / {ICON['restore']} Restore / {ICON['export']} Export[/]\n")
        self.console.print("1) Snapshot database to /reports/db_backups/")
        self.console.print("2) Restore from snapshot (typed confirm)")
        self.console.print("3) Export table → CSV")
        self.console.print("0) Back\n")
        ch = Prompt.ask("Select", default="1")
        if ch == "1":
            self._snapshot()
        elif ch == "2":
            self._restore_snapshot()
        elif ch == "3":
            t = Prompt.ask("Table name")
            if t.strip(): self._export_table_csv(t.strip())
        self._pause()

    def _screen_query_runner(self) -> None:
        self._clear(); self._render_header()
        self.console.print(f"{ICON['query']} [bold]Query Runner[/] (read-only)\n")
        self.console.print("Enter a SELECT/PRAGMA/EXPLAIN query; multi-line not supported.")
        q = Prompt.ask("SQL")
        if not q.strip(): return
        if not self._is_readonly_query(q):
            self.console.print(f"{ICON['warn']} Only read-only queries are allowed here."); self._pause(); return
        self._run_query_readonly(q)

    def _screen_diagnostics(self) -> None:
        self._clear(); self._render_header()
        self.console.print(f"{ICON['audit']} [bold]Diagnostics[/]\n")
        self._largest_tables()
        self._pause()

    def _screen_settings(self) -> None:
        self._clear(); self._render_header()
        self.console.print(f"{ICON['settings']} [bold]Settings[/]\n")
        self.console.print(f"1) Pagination size (current {self.state.page_size})")
        self.console.print(f"2) Danger mode (write ops) — currently {'ON' if self.state.danger_mode else 'OFF'}")
        self.console.print("0) Back\n")
        ch = Prompt.ask("Select", default="1")
        if ch == "1":
            self.state.page_size = IntPrompt.ask("New page size", default=self.state.page_size)
        elif ch == "2":
            if not self.state.danger_mode:
                if self._typed_confirm('ENABLE DANGER'):
                    self.state.danger_mode = True
            else:
                self.state.danger_mode = False
        self._pause()

    def _screen_help(self) -> None:
        self._clear(); self._render_header()
        self.console.print(f"{ICON['help']} Shortcuts & Safety\n")
        self.console.print("- Read-only by default; write ops require Danger mode and typed confirmation.")
        self.console.print("- Backups drop into /reports/db_backups; exports into /reports/db_console.")
        self._pause()

    # ----------------- explore helpers -----------------

    def _list_tables(self) -> None:
        """Inline list with friendly errors, never bails to outer logger."""
        try:
            rows = self._fetch_tables()
            tbl = Table(title="Tables & Views", expand=True)
            tbl.add_column("Name", style="bold")
            tbl.add_column("Type")
            tbl.add_column("Rows", justify="right")
            for name, typ in rows:
                try:
                    cnt = self._scalar_ro(f"SELECT COUNT(*) FROM [{name}]") if typ == "table" else "—"
                except Exception:
                    cnt = "?"
                tbl.add_row(name, typ, str(cnt))
            self.console.print(tbl)
        except FileNotFoundError as e:
            self.console.print(f"{ICON['err']} {e}")
            self.console.print("Tip: Launch via LaunchPad option 8 or set DB path with env var DB_CONSOLE_DB.")
        except Exception as e:
            self.console.print(f"{ICON['err']} Failed to enumerate tables: {e}")

    def _fetch_tables(self) -> list[tuple[str, str]]:
        return self._exec_ro(
            "SELECT name, type FROM sqlite_master "
            "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' "
            "ORDER BY type DESC, name ASC"
        )

    def _pick_table(self, title: str = "Pick a table/view") -> Optional[str]:
        try:
            rows = self._fetch_tables()
        except FileNotFoundError as e:
            self.console.print(f"{ICON['err']} {e}")
            self.console.print("Tip: Launch via LaunchPad option 8 or set DB path with env var DB_CONSOLE_DB.")
            return None
        except Exception as e:
            self.console.print(f"{ICON['err']} Failed to enumerate tables: {e}")
            return None

        if not rows:
            self.console.print(f"{ICON['info']} No tables/views found.")
            return None

        picker = Table(title=title, expand=True)
        picker.add_column("#", justify="right")
        picker.add_column("Name", style="bold")
        picker.add_column("Type")
        picker.add_column("Rows", justify="right")
        for i, (name, typ) in enumerate(rows, start=1):
            try:
                cnt = self._scalar_ro(f"SELECT COUNT(*) FROM [{name}]") if typ == "table" else "—"
            except Exception:
                cnt = "?"
            picker.add_row(str(i), name, typ, str(cnt))
        self.console.print(picker)

        pick = IntPrompt.ask("Pick # (0=cancel)", default=0)
        if 1 <= pick <= len(rows):
            return rows[pick - 1][0]
        return None

    def _show_schema(self, table: str) -> None:
        info = self._exec_ro(f"SELECT sql FROM sqlite_master WHERE name=? AND type IN ('table','view')", (table,))
        idxs = self._exec_ro(f"PRAGMA index_list({table})")
        fks = self._exec_ro(f"PRAGMA foreign_key_list({table})")
        trigs = self._exec_ro(f"SELECT name, sql FROM sqlite_master WHERE tbl_name=? AND type='trigger'", (table,))

        self.console.print(Panel(Text(info[0][0] if info and info[0][0] else "(no CREATE SQL)"), title=f"{ICON['schema']} CREATE for {table}", border_style="green"))
        if idxs:
            t = Table(title="Indexes", expand=True); t.add_column("seq"); t.add_column("name"); t.add_column("unique")
            for row in idxs: t.add_row(*[str(x) for x in row[:3]])
            self.console.print(t)
        if fks:
            t = Table(title="Foreign Keys", expand=True); t.add_column("id"); t.add_column("seq"); t.add_column("table"); t.add_column("from"); t.add_column("to"); t.add_column("on_update"); t.add_column("on_delete")
            for row in fks: t.add_row(str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5]), str(row[6]))
            self.console.print(t)
        if trigs:
            t = Table(title="Triggers", expand=True); t.add_column("name"); t.add_column("sql")
            for name, sql in trigs: t.add_row(str(name), str(sql or ""))
            self.console.print(t)

    def _view_rows_paged(self, table: str) -> None:
        total = self._scalar_ro(f"SELECT COUNT(*) FROM [{table}]")
        page = 0
        size = self.state.page_size
        while True:
            rows = self._exec_ro(f"SELECT * FROM [{table}] LIMIT ? OFFSET ?", (size, page*size))
            if not rows and page == 0:
                self.console.print(f"{ICON['info']} Table is empty."); break
            cols = [d[0] for d in self._columns(f"SELECT * FROM [{table}] LIMIT 0")]
            t = Table(title=f"{ICON['rows']} {table} — page {page+1} ({size} rows/page) — total {total}", expand=True, show_lines=False)
            for c in cols: t.add_column(c)
            for r in rows: t.add_row(*[self._short(v) for v in r])
            self.console.print(t)
            nav = Prompt.ask("[N]ext / [P]rev / [Q]uit", default="n").lower()
            if nav.startswith("n"): page += 1
            elif nav.startswith("p") and page > 0: page -= 1
            else: break

    # ----------------- DataLocker -----------------

    def _dl_system_vars(self) -> None:
        if DataLocker is None:
            self.console.print(f"{ICON['warn']} DataLocker not available."); return
        dl = DataLocker.get_instance()
        sysm = getattr(dl, "system", None)
        if not sysm or not hasattr(sysm, "list_vars"):
            self.console.print(f"{ICON['warn']} System var manager unavailable."); return
        rows = sysm.list_vars()  # expected [(key, value_json, updated_at), ...]
        t = Table(title=f"{ICON['sysvars']} System Vars", expand=True)
        t.add_column("Key"); t.add_column("Value"); t.add_column("Updated")
        for r in rows:
            key = str(r[0]); val = self._short(r[1]); upd = str(r[2]) if len(r) >= 3 else "—"
            t.add_row(key, val, upd)
        self.console.print(t)

        if Confirm.ask("Edit a var?"):
            key = Prompt.ask("Key")
            raw = Prompt.ask("New JSON value (or blank to cancel)")
            if raw.strip():
                try:
                    json.loads(raw)
                except Exception as e:
                    self.console.print(f"{ICON['warn']} Invalid JSON: {e}"); return
                sysm.set_var(key, json.loads(raw))
                self.console.print(f"{ICON['ok']} Set {key}.")

    def _dl_wallets(self) -> None:
        if DataLocker is None:
            self.console.print(f"{ICON['warn']} DataLocker not available."); return
        dl = DataLocker.get_instance()
        rows = []
        try:
            if hasattr(dl, "read_wallets"):
                rows = dl.read_wallets() or []
            elif hasattr(dl, "wallets") and hasattr(dl.wallets, "get_wallets"):
                rows = dl.wallets.get_wallets() or []
        except Exception as e:
            self.console.print(f"{ICON['warn']} Could not read wallets: {e}")
        t = Table(title=f"{ICON['wallets']} Wallets", expand=True)
        t.add_column("Name"); t.add_column("Address"); t.add_column("Active")
        for w in rows:
            t.add_row(str(w.get("name","—")), str(w.get("public_address") or w.get("address") or "—"), "🟢" if w.get("is_active", True) else "🔴")
        self.console.print(t)
        if not rows: return
        if Confirm.ask("Toggle active on a wallet?"):
            name = Prompt.ask("Name (exact)")
            match = next((w for w in rows if str(w.get("name")) == name), None)
            if not match:
                self.console.print(f"{ICON['warn']} No wallet named {name}."); return
            new_state = not bool(match.get("is_active", True))
            try:
                if hasattr(dl, "update_wallet"):
                    dl.update_wallet({**match, "is_active": new_state})
                else:
                    # fallback: set_var in system namespace
                    sysm = getattr(dl, "system", None)
                    if sysm:
                        sysm.set_var(f"wallet_active::{match.get('name')}", new_state)
                self.console.print(f"{ICON['ok']} {name} -> {'active' if new_state else 'inactive'}.")
            except Exception as e:
                self.console.print(f"{ICON['warn']} Toggle failed: {e}")

    # ----------------- maintenance -----------------

    def _pragma_check(self, which: str) -> None:
        rows = self._exec_ro(f"PRAGMA {which}")
        t = Table(title=f"{ICON['integrity']} {which}", expand=True); t.add_column("result")
        for r in rows: t.add_row(" | ".join([str(x) for x in r]))
        self.console.print(t)

    def _fk_check(self) -> None:
        rows = self._exec_ro("PRAGMA foreign_key_check")
        t = Table(title=f"{ICON['fk']} foreign_key_check", expand=True)
        t.add_column("table"); t.add_column("rowid"); t.add_column("ref-table"); t.add_column("fkid")
        if not rows:
            self.console.print(f"{ICON['ok']} No FK violations.")
            return
        for r in rows: t.add_row(*[str(x) for x in r])
        self.console.print(t)

    def _toggle_foreign_keys(self) -> None:
        current = bool(self._get_pragma("foreign_keys"))
        target = not current
        if not self._danger_confirm(f"Toggle foreign_keys to {'ON' if target else 'OFF'}"): return
        with self._conn_rw() as con:
            con.execute(f"PRAGMA foreign_keys={'ON' if target else 'OFF'}")
        self.console.print(f"{ICON['ok']} foreign_keys -> {'ON' if target else 'OFF'}.")

    def _toggle_wal(self) -> None:
        current = str(self._get_pragma("journal_mode")).lower()
        target = "wal" if current != "wal" else "delete"
        if not self._danger_confirm(f"Switch journal_mode to {target.upper()}"): return
        with self._conn_rw() as con:
            cur = con.execute(f"PRAGMA journal_mode={target}")
            cur.fetchall()
        self.console.print(f"{ICON['ok']} journal_mode -> {target.upper()}.")

    def _vacuum(self) -> None:
        if not self._danger_confirm("Run VACUUM (exclusive lock)"): return
        with self._conn_rw() as con:
            con.execute("VACUUM")
        self.console.print(f"{ICON['ok']} VACUUM complete.")

    def _analyze(self) -> None:
        if not self._danger_confirm("Run ANALYZE"): return
        with self._conn_rw() as con:
            con.execute("ANALYZE")
        self.console.print(f"{ICON['ok']} ANALYZE complete.")

    def _reindex(self) -> None:
        if not self._danger_confirm("Run REINDEX"): return
        with self._conn_rw() as con:
            con.execute("REINDEX")
        self.console.print(f"{ICON['ok']} REINDEX complete.")

    # ----------------- wizards -----------------

    def _wiz_normalize_liquid_keys(self) -> None:
        if DataLocker is None:
            self.console.print(f"{ICON['warn']} DataLocker not available."); return
        dl = DataLocker.get_instance(); sysm = getattr(dl, "system", None)
        if not sysm:
            self.console.print(f"{ICON['warn']} System manager unavailable."); return
        cfg = sysm.get_var("liquid_monitor") or {}
        if isinstance(cfg, dict) and "asset_thresholds" in cfg and "thresholds" not in cfg:
            cfg["thresholds"] = dict(cfg.get("asset_thresholds") or {})
            if self._danger_confirm("Apply normalization (asset_thresholds → thresholds)?"):
                sysm.set_var("liquid_monitor", cfg)
                self.console.print(f"{ICON['ok']} Normalized liquid_monitor.")
        else:
            self.console.print(f"{ICON['info']} Nothing to normalize.")

    def _wiz_reseed_configs(self) -> None:
        if DataLocker is None:
            self.console.print(f"{ICON['warn']} DataLocker not available."); return
        dl = DataLocker.get_instance(); sysm = getattr(dl, "system", None)
        if not sysm:
            self.console.print(f"{ICON['warn']} System manager unavailable."); return
        # Best-effort defaults
        liquid = sysm.get_var("liquid_monitor")
        if not liquid:
            liquid = {"enabled": True, "threshold_percent": 5.0, "thresholds": {"BTC": 5.0, "ETH": 5.0, "SOL": 5.0}, "notifications": {"system": True}}
            sysm.set_var("liquid_monitor", liquid)
        alerts = sysm.get_var("alert_thresholds")
        if not alerts:
            alerts = {"thresholds": {"BTC": 5.0, "ETH": 5.0, "SOL": 5.0}}
            sysm.set_var("alert_thresholds", alerts)
        self.console.print(f"{ICON['ok']} Reseed complete (if missing).")

    def _wiz_cleanse_alerts(self) -> None:
        # If there is a DL method for cleansing alert IDs, call it; otherwise no-op
        if DataLocker is None:
            self.console.print(f"{ICON['warn']} DataLocker not available."); return
        dl = DataLocker.get_instance()
        if hasattr(dl, "cleanse_alert_ids"):
            try:
                dl.cleanse_alert_ids()
                self.console.print(f"{ICON['ok']} Cleanse complete.")
            except Exception as e:
                self.console.print(f"{ICON['warn']} Cleanse failed: {e}")
        else:
            self.console.print(f"{ICON['info']} No cleanse method.")

    # ----------------- backup / restore / export -----------------

    def _snapshot(self) -> None:
        ts = time.strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(BACKUP_DIR, f"mother_{ts}.db")
        try:
            # Use SQLite backup API for consistency
            with self._conn_ro() as src, sqlite3.connect(dest) as dst:
                src.backup(dst)
            self.console.print(f"{ICON['ok']} Snapshot saved: {dest}")
        except Exception as e:
            self.console.print(f"{ICON['err']} Snapshot failed: {e}")

    def _restore_snapshot(self) -> None:
        files = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".db")]
        if not files:
            self.console.print(f"{ICON['warn']} No snapshots in {BACKUP_DIR}."); return
        files.sort(reverse=True)
        t = Table(title="Available Snapshots", expand=True); t.add_column("#"); t.add_column("file")
        for i,f in enumerate(files, 1): t.add_row(str(i), f)
        self.console.print(t)
        pick = IntPrompt.ask("Pick file # to restore (dangerous!)", default=1)
        if not (1 <= pick <= len(files)): self.console.print(f"{ICON['warn']} Invalid pick."); return
        fname = files[pick-1]
        if not self._danger_confirm(f"RESTORE {fname}"): return
        src_path = os.path.join(BACKUP_DIR, fname)
        try:
            with sqlite3.connect(src_path) as src, self._conn_rw() as dst:
                src.backup(dst)
            self.console.print(f"{ICON['ok']} Restored snapshot {fname}.")
        except Exception as e:
            self.console.print(f"{ICON['err']} Restore failed: {e}")

    def _export_table_csv(self, table: str) -> None:
        path = os.path.join(EXPORT_DIR, f"{table}.csv")
        try:
            with open(path, "w", encoding="utf-8") as f:
                with self._conn_ro() as con:
                    cur = con.execute(f"SELECT * FROM [{table}]")
                    cols = [d[0] for d in cur.description]
                    f.write(",".join(cols) + "\n")
                    for row in cur.fetchall():
                        vals = [self._csv_escape(v) for v in row]
                        f.write(",".join(vals) + "\n")
            self.console.print(f"{ICON['ok']} Exported → {path}")
        except Exception as e:
            self.console.print(f"{ICON['err']} Export failed: {e}")

    # ----------------- diagnostics -----------------

    def _largest_tables(self) -> None:
        rows = self._exec_ro("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name
        """)
        stats: List[Tuple[str, int]] = []
        for (name,) in rows:
            try:
                cnt = self._scalar_ro(f"SELECT COUNT(*) FROM [{name}]")
            except Exception:
                cnt = -1
            stats.append((name, cnt))
        stats.sort(key=lambda x: x[1], reverse=True)
        t = Table(title=f"{ICON['heavy']} Largest tables (by row count)", expand=True)
        t.add_column("Table"); t.add_column("Rows", justify="right")
        for name, cnt in stats:
            t.add_row(name, "—" if cnt < 0 else str(cnt))
        self.console.print(t)

    # ----------------- query runner -----------------

    def _is_readonly_query(self, q: str) -> bool:
        q = q.strip().lower()
        return q.startswith("select") or q.startswith("pragma") or q.startswith("explain")

    def _run_query_readonly(self, q: str) -> None:
        try:
            rows = self._exec_ro(q)
            cols = [d[0] for d in self._columns(q)]
            t = Table(title="Query Result", expand=True)
            for c in cols: t.add_column(c)
            for r in rows: t.add_row(*[self._short(v) for v in r])
            self.console.print(t)
        except Exception as e:
            self.console.print(f"{ICON['err']} Query failed: {e}")

    # ----------------- DB utils -----------------

    def _detect_db_path(self) -> str:
        """Find a real mother.db; never guess blindly."""
        env_db = os.environ.get(DB_CONSOLE_ENV)
        if env_db and os.path.exists(env_db):
            return env_db

        try:
            if DataLocker is not None:
                dl = DataLocker.get_instance()
                dbp = getattr(getattr(dl, "db", None), "db_path", None)
                if dbp and os.path.exists(dbp):
                    return dbp
        except Exception:
            pass

        base_dir = os.path.abspath(os.path.dirname(__file__))
        candidates = [
            os.path.join(os.getcwd(), "backend", "mother.db"),
            os.path.join(REPO_ROOT, "backend", "mother.db"),
            os.path.join(REPO_ROOT, "mother.db"),
            os.path.join(base_dir, "..", "mother.db"),
            os.path.join(base_dir, "..", "..", "mother.db"),
        ]
        for p in candidates:
            candidate = os.path.abspath(p)
            if os.path.exists(candidate):
                return candidate
        return DEFAULT_DB

    def _conn_ro(self) -> sqlite3.Connection:
        """Read-only connection that fails loudly if file missing."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        uri = f"file:{self.db_path}?mode=ro"
        con = sqlite3.connect(uri, uri=True, check_same_thread=False)
        con.row_factory = sqlite3.Row
        return con

    def _conn_rw(self) -> sqlite3.Connection:
        if not self.state.danger_mode:
            raise RuntimeError("Danger mode is OFF; write connection not allowed.")
        con = sqlite3.connect(self.db_path, check_same_thread=False)
        con.row_factory = sqlite3.Row
        return con

    def _exec_ro(self, sql: str, params: Tuple[Any, ...] = ()) -> List[Tuple[Any, ...]]:
        with self._conn_ro() as con:
            cur = con.execute(sql, params)
            return cur.fetchall()

    def _scalar_ro(self, sql: str, params: Tuple[Any, ...] = ()) -> Any:
        with self._conn_ro() as con:
            cur = con.execute(sql, params)
            row = cur.fetchone()
            return row[0] if row is not None else None

    def _columns(self, sql: str) -> List[Tuple]:
        with self._conn_ro() as con:
            cur = con.execute(sql)
            return cur.description or []

    def _get_pragma(self, name: str) -> Any:
        try:
            rows = self._exec_ro(f"PRAGMA {name}")
            if not rows: return None
            val = rows[0][0]
            if name == "foreign_keys":
                return bool(val)
            return val
        except Exception:
            return None

    # ----------------- misc helpers -----------------

    def _file_size(self, path: str) -> str:
        try:
            n = os.path.getsize(path)
        except Exception:
            return "—"
        units = ["B","KB","MB","GB","TB"]
        i = 0
        while n >= 1024 and i < len(units)-1:
            n /= 1024.0; i += 1
        return f"{n:.1f}{units[i]}"

    def _db_pages(self) -> int:
        try:
            psize = int(self._scalar_ro("PRAGMA page_size") or 0)
            pcnt  = int(self._scalar_ro("PRAGMA page_count") or 0)
            return pcnt
        except Exception:
            return 0

    def _short(self, v: Any, maxlen: int = 80) -> str:
        s = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
        return s if len(s) <= maxlen else s[:maxlen-1] + "…"

    def _csv_escape(self, v: Any) -> str:
        if v is None: return ""
        s = str(v)
        if any(c in s for c in [",", "\"", "\n"]):
            return '"' + s.replace('"','""') + '"'
        return s

    def _typed_confirm(self, token: str) -> bool:
        self.console.print(f"Type [bold]{token}[/] to confirm.")
        return Prompt.ask("Confirm") == token

    def _danger_confirm(self, msg: str) -> bool:
        if not self.state.danger_mode:
            self.console.print(f"{ICON['warn']} Danger mode is OFF. Enable it in Settings."); return False
        self.console.print(f"{ICON['warn']} {msg}")
        return self._typed_confirm("PROCEED")

    def _clear(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")

    def _pause(self) -> None:
        self.console.print(Text("\nPress [Enter] to continue…", style="dim"))
        try: input()
        except KeyboardInterrupt: pass


def run_db_console(db_path: Optional[str] = None) -> None:
    DbConsoleService(db_path=db_path).run_console()


if __name__ == "__main__":
    run_db_console()
