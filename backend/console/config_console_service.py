# backend/console/config_console_service.py
from __future__ import annotations

import json
import os
from typing import Optional, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from backend.core.config_core import (
    ConfigCore,
    PrecedencePolicy,
    DEFAULT_SONIC_MONITOR_CONFIG,
)
from backend.core.config_core.validators import validate_sonic_monitor

ICON = {
    "cfg": "🧩", "ok": "✅", "warn": "⚠️", "err": "❌",
    "policy": "⚖️", "json": "📄", "db": "🗄️", "env": "🌱",
    "save": "💾", "edit": "✏️", "back": "↩️",
}

class ConfigConsoleService:
    """Interactive console for the Sonic Monitor config via ConfigCore."""
    def __init__(self, json_path: Optional[str] = None):
        self.console = Console()
        self.core = ConfigCore(PrecedencePolicy.JSON_FIRST, json_path=json_path)
        self.working: Dict[str, Any] = {}

    # ---- entry ----
    def run_console(self) -> None:
        while True:
            cfg, meta = self.core.load("sonic_monitor")
            if not self.working:
                # start with the effective config as the working copy
                self.working = json.loads(json.dumps(cfg))

            self._clear()
            self._header(meta)

            self.console.print(
                "1) View effective\n"
                "2) Edit working (JSON)\n"
                "3) Validate working\n"
                "4) Save working (JSON + DB)\n"
                "5) Toggle precedence (JSON_FIRST/DB_FIRST)\n"
                "6) Reset working to defaults (not saved)\n"
                "7) Show sources\n"
                "0) Exit\n"
            )
            choice = Prompt.ask("Select", default="1")

            if choice == "1":
                self._show_json(cfg, "Effective config")
            elif choice == "2":
                self.working = self._edit_json(self.working)
            elif choice == "3":
                self._validate_json(self.working)
            elif choice == "4":
                self._save_working()
                # reload effective after save
                self.working, _ = self.core.load("sonic_monitor")
            elif choice == "5":
                self._toggle_precedence()
            elif choice == "6":
                self.working = json.loads(json.dumps(DEFAULT_SONIC_MONITOR_CONFIG))
                self.console.print(f"{ICON['warn']} Working copy reset to defaults (not saved).")
                self._pause()
            elif choice == "7":
                self._show_sources(meta)
            elif choice in {"0", "q", "Q", "exit"}:
                return
            else:
                self.console.print(f"{ICON['warn']} Invalid selection.")
                self._pause()

    # ---- sections ----
    def _header(self, meta: Dict[str, Any]) -> None:
        errs = len(meta.get("errors", []))
        warns = len(meta.get("warnings", []))
        pol = meta.get("policy", "JSON_FIRST")
        hdr = Text.assemble(
            (f" {ICON['cfg']} Config Console — sonic_monitor  ", "bold white"),
            (f"| {ICON['policy']} {pol}  ", "cyan"),
            (f"| {ICON['ok']}0 {ICON['warn']}{warns} {ICON['err']}{errs}  ", "magenta"),
        )
        self.console.print(Panel(hdr, border_style="cyan"))

    def _show_json(self, obj: Dict[str, Any], title: str) -> None:
        txt = json.dumps(obj, indent=2, ensure_ascii=False)
        self.console.print(Panel(Text(txt), title=title, border_style="green"))
        self._pause()

    def _validate_json(self, obj: Dict[str, Any]) -> None:
        errors, warnings = validate_sonic_monitor(obj)
        if not errors and not warnings:
            self.console.print(f"{ICON['ok']} Looks good.")
        if errors:
            self.console.print("\n[bold]Errors:[/]")
            for e in errors:
                self.console.print(f"{ICON['err']} {e}")
        if warnings:
            self.console.print("\n[bold]Warnings:[/]")
            for w in warnings:
                self.console.print(f"{ICON['warn']} {w}")
        self._pause()

    def _save_working(self) -> None:
        res = self.core.save("sonic_monitor", self.working, also_write_legacy=True)
        if res.get("ok"):
            jp = res.get("json_path")
            dk = res.get("db_key")
            self.console.print(f"{ICON['ok']} Saved {ICON['json']} {jp} and {ICON['db']} {dk}.")
        else:
            self.console.print(f"{ICON['err']} Save failed: {res.get('errors')}")
        self._pause()

    def _show_sources(self, meta: Dict[str, Any]) -> None:
        t = Table(title="Sources", expand=True)
        t.add_column("Layer"); t.add_column("Location")
        src = meta.get("sources", {})
        t.add_row("JSON", str(src.get("json")))
        t.add_row("DB",   str(src.get("db")))
        t.add_row("ENV",  str(src.get("env")))
        self.console.print(t)
        self._pause()

    def _toggle_precedence(self) -> None:
        newp = (PrecedencePolicy.DB_FIRST
                if self.core.policy is PrecedencePolicy.JSON_FIRST
                else PrecedencePolicy.JSON_FIRST)
        self.core.set_precedence(newp)
        self.console.print(f"{ICON['policy']} Precedence -> {newp.name}")
        self._pause()

    # ---- io helpers ----
    def _edit_json(self, current: Dict[str, Any]) -> Dict[str, Any]:
        self.console.print("Paste JSON for the working copy. Finish with a blank line.")
        buf = []
        while True:
            line = input("json> ")
            if not line.strip() and buf:
                break
            buf.append(line)
        raw = "\n".join(buf).strip()
        if not raw:
            self.console.print("(cancelled)")
            self._pause()
            return current
        try:
            new_cfg = json.loads(raw)
            self.console.print(f"{ICON['ok']} Parsed.")
            self._pause()
            return new_cfg
        except Exception as e:
            self.console.print(f"{ICON['err']} Invalid JSON: {e}")
            self._pause()
            return current

    def _pause(self) -> None:
        self.console.print(Text("\nPress [Enter] to continue…", style="dim"))
        try:
            input()
        except KeyboardInterrupt:
            pass

    def _clear(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")


def run_config_console(json_path: Optional[str] = None) -> None:
    ConfigConsoleService(json_path=json_path).run_console()


if __name__ == "__main__":
    run_config_console()
