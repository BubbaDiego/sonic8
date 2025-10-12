#!/usr/bin/env python3
"""
🌀 Sonic Launch Pad (sonic7)
Feature-parity with sonic6: venv re-exec, menu order, background launches,
and optional integrations (Perps, Cyclone, Fun Console, Wallet UI).
"""

from __future__ import annotations

import contextlib
import io
import os
import shutil
import sys
import subprocess
import shlex
import platform
import webbrowser
import time
import importlib
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Sequence, Optional, Dict

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

# --- spec toolchain bootstrap (ensures cwd/PYTHONPATH + pyyaml/jsonschema) ---
try:
    from backend.scripts.spec_bootstrap import preflight as spec_preflight
except Exception:
    spec_preflight = None

# ──────────────────────────────────────────────────────────────────────────────
# Preferred interpreter logic:
# - If .venv exists, ALWAYS re-exec Launch Pad under that interpreter
# - Otherwise fall back to whatever launched this process.
# - Print the interpreter once so you can sanity-check quickly.
# - All subprocesses (uvicorn, maintenance scripts) must use PYTHON_EXEC.
# ──────────────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent
if os.name == "nt":
    _venv_py = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
else:
    _venv_py = ROOT_DIR / ".venv" / "bin" / "python"
PYTHON_EXEC = str(_venv_py) if _venv_py.exists() else sys.executable

if Path(PYTHON_EXEC).resolve() != Path(sys.executable).resolve():
    if os.environ.get("LAUNCHPAD_REEXEC") != "1":
        os.environ["LAUNCHPAD_REEXEC"] = "1"
        print(f"[LaunchPad] Re-exec under venv: {PYTHON_EXEC}")
        os.execv(PYTHON_EXEC, [PYTHON_EXEC, __file__] + sys.argv[1:])

print(f"[LaunchPad] python={PYTHON_EXEC}")

# Optional rich UI; fall back to plain text if not installed
Panel = None  # type: ignore
try:
    from rich.console import Console  # type: ignore
    from rich.panel import Panel  # type: ignore
    console = Console()
except Exception:
    class _Bare:
        def print(self, *a, **k):
            print(*a)
        def log(self, *a, **k):
            print(*a)
    console = _Bare()  # type: ignore
try:
    from pyfiglet import Figlet  # type: ignore
except Exception:
    Figlet = None

BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

ICON = {
    "frontend": "🌐",
    "backend": "🛠️",
    "full_stack": "🔄",
    "monitor": "📡",
    "apps": "🧩",
    "hog": "🦔",
    "rocket": "🚀",
    "verify_db": "🗄️",
    "tests": "🧪",
    "wallet": "💼",
    "cyclone": "🌀",
    "test_ui": "🧪🖥️",
    "perps": "🛰️",
    "goals": "🎯",
    "maintenance": "🧹",
    "exit": "⏻",
}

def repo_root() -> Path:
    return ROOT_DIR


def _quote_win(arg: str) -> str:
    if " " in arg or "'" in arg or '"' in arg:
        return f'"{arg}"'
    return arg


def run_in_console(
    cmd: Sequence[str],
    cwd: Path | None = None,
    title: str = "",
    new_window: bool = False,
    env: Optional[Dict[str, str]] = None,
) -> int:
    """Run a command in current console or a new terminal window (Windows/macOS/Linux)."""
    workdir = Path(cwd) if cwd is not None else repo_root()
    workdir_str = str(workdir)
    env = (os.environ.copy() | env) if env else os.environ.copy()

    if new_window:
        if os.name == "nt":
            joined = " ".join(_quote_win(a) for a in cmd)
            subprocess.Popen(
                f'start "{title or "Sonic"}" cmd /k {joined}',
                cwd=workdir_str,
                shell=True,
                env=env,
            )
            return 0
        if sys.platform == "darwin":
            osa = (
                "osascript -e 'tell app \"Terminal\" to do script \""
                f"cd {workdir_str} && {' '.join(shlex.quote(a) for a in cmd)}\"'"
            )
            subprocess.Popen(osa, shell=True, env=env)
            return 0
        term = shutil.which("gnome-terminal") or shutil.which("xterm")
        if term and "gnome-terminal" in term:
            subprocess.Popen(
                [
                    term, "--", "bash", "-lc",
                    f"cd {workdir_str} && {' '.join(shlex.quote(a) for a in cmd)}",
                ],
                env=env,
            )
            return 0
        if term:
            subprocess.Popen(
                [
                    term, "-e",
                    f"bash -lc \"cd {workdir_str} && {' '.join(shlex.quote(a) for a in cmd)}\"",
                ],
                env=env,
            )
            return 0
        return subprocess.call(cmd, cwd=workdir_str, env=env)

    return subprocess.call(cmd, cwd=workdir_str, env=env)


def wait_and_open(url: str, secs: float = 3.0) -> None:
    try:
        time.sleep(secs)
        webbrowser.open(url)
    except Exception:
        pass


# ── Sticky output + logging ─────────────────────────────────
_STICKY_HOLD = True
_LOG_DIR = Path("reports/launchpad_logs")


class _Tee(io.TextIOBase):
    def __init__(self, *streams):
        self._streams = streams

    def write(self, s):
        for st in self._streams:
            try:
                st.write(s)
            except Exception:
                pass
        return len(s)

    def flush(self):
        for st in self._streams:
            try:
                st.flush()
            except Exception:
                pass


def _pause_after_action():
    try:
        input("\n⏸  Press ENTER to return to the menu…")
    except KeyboardInterrupt:
        pass


class _ActionCapture:
    """Tee stdout/stderr to console and a per-action log."""

    def __init__(self, label: str):
        safe = (label or "action").strip().replace(" ", "_").replace("/", "_")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.path = _LOG_DIR / f"{safe}_{ts}.log"
        self._buf = io.StringIO()

    def __enter__(self):
        self._tee_out = _Tee(sys.__stdout__, self._buf)
        self._tee_err = _Tee(sys.__stderr__, self._buf)
        self._out_cm = contextlib.redirect_stdout(self._tee_out)
        self._err_cm = contextlib.redirect_stderr(self._tee_err)
        self._out_cm.__enter__()
        self._err_cm.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._err_cm.__exit__(exc_type, exc, tb)
        self._out_cm.__exit__(exc_type, exc, tb)
        try:
            self.path.write_text(self._buf.getvalue(), encoding="utf-8")
            print(f"\n📄 Log saved: {self.path}")
        except Exception:
            pass
        if exc_type:
            traceback.print_exception(exc_type, exc, tb, file=sys.__stdout__)
        return False


def run_menu_action(label: str, fn):
    if not callable(fn):
        print(f"[WARN] Not a callable action: {label}")
        if _STICKY_HOLD:
            _pause_after_action()
        return
    result = None
    with _ActionCapture(label):
        try:
            result = fn()
        except SystemExit:
            # allow actions to exit without killing the menu
            pass
        except Exception:
            # traceback/log handled by _ActionCapture.__exit__
            pass
    if _STICKY_HOLD:
        _pause_after_action()
    return result


# ──────────────────────────── Actions ─────────────────────────────────────────

def launch_frontend() -> None:
    console.log("🚀 Launching Sonic/Vite frontend…")
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        console.log("📦 Installing frontend dependencies (npm install)…")
        try:
            subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, check=False)
        except Exception as exc:
            console.log(f"[yellow]npm install encountered an issue: {exc}[/]")
    fe_cmd = ["npm", "run", "dev", "--", "--port", "3000", "--strictPort", "--host"]
    run_in_console(fe_cmd, FRONTEND_DIR, title="Frontend", new_window=True)
    console.log("[green]Frontend starting on http://localhost:3000 (strict)[/]")


def launch_backend(
    host: str = "127.0.0.1",
    port: int = 5000,
    reload: bool = True,
    open_browser: bool = True,
    setup: bool = False,
) -> None:
    console.log("🛠️ Launching FastAPI backend…")
    if os.name == "nt":
        ps_runner = ROOT_DIR / "scripts" / "console" / "run_backend.ps1"
        if ps_runner.exists():
            host_arg = ["-Host", host, "-Port", str(port)]
            cmd = [
                "powershell",
                "-ExecutionPolicy", "Bypass",
                "-File", str(ps_runner),
            ] + host_arg
            if reload:
                cmd.append("-Reload")
            if open_browser:
                cmd.append("-OpenBrowser")
            if setup:
                cmd.append("-Setup")
            run_in_console(cmd, ROOT_DIR, title="Sonic - FastAPI Backend", new_window=True)
            console.log(f"[green]Backend running at http://{host}:{port}[/]")
            return
    # Fallback: uvicorn directly
    cmd = [
        PYTHON_EXEC, "-m", "uvicorn",
        "backend.sonic_backend_app:app",
        "--host", host, "--port", str(port),
    ]
    if reload:
        cmd.append("--reload")
    run_in_console(cmd, BACKEND_DIR, title="Sonic - FastAPI Backend", new_window=True)
    if open_browser:
        wait_and_open(f"http://{host}:{port}/docs")
    console.log(f"[green]Backend running at http://{host}:{port}[/]")


def launch_full_stack():
    launch_backend()
    launch_frontend()
    console.log("[green]Full stack running in background.[/]")


def launch_sonic_monitor():
    console.log("📡 Launching Sonic Monitor…")
    # Use the foldered monitor entry (works with your import guards)
    run_in_console(
        [PYTHON_EXEC, "sonic_monitor.py"],
        BACKEND_DIR / "core" / "monitor_core",
        title="🦔 Sonic Monitor 🦔",
        new_window=True,
    )
    console.log("[green]Sonic Monitor started in background.[/]")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def perps_menu_config_path() -> Path:
    return repo_root() / "backend" / "config" / "unified_jupiter_menu.json"


def _read_perps_keypair_from_json(default: str = "") -> str:
    try:
        cfg = perps_menu_config_path()
        if cfg.exists():
            data = json.loads(_read(cfg) or "{}")
            keypair = data.get("keypair") or default
            return str(keypair)
    except Exception:
        pass
    return default


def preflight_perps() -> list[str]:
    errors: list[str] = []
    if not shutil.which("node"):
        errors.append("Node.js not found on PATH (required for TS runner).")
    keypair = _read_perps_keypair_from_json() or os.getenv("JUPITER_KEYPAIR", "")
    if not keypair:
        errors.append("Keypair path not configured (backend/config/unified_jupiter_menu.json).")
    else:
        if not Path(keypair).expanduser().exists():
            errors.append(f"Keypair file missing: {keypair}")
    return errors


def launch_perps_console(new_window: bool = False) -> int:
    """Launch the Unified Perps console application."""
    errs = preflight_perps()
    if errs:
        console.print("\n[bold red][Perps] Preflight failed:[/bold red]")
        for e in errs:
            console.print(f"  • {e}")
        console.print("Fix the above and try again.\n")
        return 1
    script = repo_root() / "backend" / "scripts" / "unified_jupiter_menu.py"
    if not script.exists():
        console.print("[yellow]Unified Perps Menu script not found.[/]")
        return 1
    cmd = [PYTHON_EXEC, str(script)]
    console.print("\n[bold cyan][Perps][/bold cyan] Launching Unified Perps Menu…\n")
    return run_in_console(cmd, cwd=repo_root(), title="Perps Console", new_window=new_window)


def launch_cyclone_app(new_window: bool = False) -> int:
    """
    Cyclone App launcher:
      1) Try in-process import+call if backend.console package exists.
      2) Else run script path fallback (service or legacy).
    """
    root = repo_root()
    pkg_dir = root / "backend" / "console"
    if pkg_dir.exists() and (pkg_dir / "__init__.py").exists():
        print("\n[Cyclone] Launching Cyclone console in-process…\n")
        try:
            # Prefer the service entrypoint if present
            try:
                mod = importlib.import_module("backend.console.cyclone_console_service")
                fn = getattr(mod, "run_cyclone_console", None)
                if callable(fn):
                    fn(poll_interval=60)
                    return 0
            except ModuleNotFoundError:
                pass
            # Fallback to legacy run_console()
            mod = importlib.import_module("backend.console.cyclone_console")
            fn = getattr(mod, "run_console", None)
            if callable(fn):
                fn()
                return 0
            print("[Cyclone] In-process entry not found (run_cyclone_console / run_console missing).")
        except Exception as e:
            print(f"[Cyclone] In-process import failed: {e!r} — falling back to script.")

    # 2) Script path fallback (no package import needed)
    py = PYTHON_EXEC
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) if "PYTHONPATH" not in env else f"{root}{os.pathsep}{env['PYTHONPATH']}"

    service = root / "backend" / "console" / "cyclone_console_service.py"
    legacy  = root / "backend" / "console" / "cyclone_console.py"
    if service.exists():
        print("\n[Cyclone] Launching via script: backend\\console\\cyclone_console_service.py\n")
        return run_in_console([py, str(service)], cwd=root, title="Cyclone App", new_window=new_window, env=env)
    if legacy.exists():
        print("\n[Cyclone] Launching via script: backend\\console\\cyclone_console.py\n")
        return run_in_console([py, str(legacy)], cwd=root, title="Cyclone App", new_window=new_window, env=env)

    print("[Cyclone] No console entry found.")
    print("  Looked for:")
    print("   - backend\\console\\cyclone_console_service.py")
    print("   - backend\\console\\cyclone_console.py")
    try:
        import glob
        matches = glob.glob(str(root / "backend" / "**" / "*cyclone_console*.py"), recursive=True)
        if matches:
            print("  Found:")
            for m in matches:
                print("   •", m)
    except Exception:
        pass
    return 1


def verify_database():
    script = ROOT_DIR / "scripts" / "verify_all_tables_exist.py"
    if script.exists():
        subprocess.call([PYTHON_EXEC, str(script)])
    else:
        console.log("[yellow]scripts/verify_all_tables_exist.py not found.[/]")


def run_tests():
    console.log("🧪 Running tests…")
    # Try internal runner first; else pytest; else message.
    try:
        from test_core import TestCoreRunner, formatter  # type: ignore
        results = TestCoreRunner().run()
        console.print(formatter.render_summary(results))
        return
    except Exception:
        pass
    try:
        subprocess.run([PYTHON_EXEC, "-m", "pytest", "-q"], cwd=str(ROOT_DIR), check=False)
    except Exception as exc:
        console.print(f"[yellow]No test runner available ({exc}).[/]")


def run_test_console():
    try:
        from test_core import get_console_ui  # type: ignore
        TestConsoleUI = get_console_ui()
        TestConsoleUI().start()
    except Exception:
        console.print("[yellow]Test Console UI not available.[/]")


def run_fun_console():
    try:
        subprocess.run([PYTHON_EXEC, "-m", "backend.core.fun_core.console"], check=False)
    except Exception:
        console.print("[yellow]Fun Console not available.[/]")


def wallet_menu():
    """Interactive, capability-aware Wallet Manager (works with whatever wallet_core provides)."""
    # Lazy imports; we don't assume all modules exist in sonic7
    svc = None
    core = None
    try:
        from backend.core.wallet_core import WalletService as _WalletService  # type: ignore
        svc = _WalletService()
    except Exception:
        pass
    try:
        # Optional orchestrator for balance refresh and chain ops
        from backend.core.wallet_core import WalletCore as _WalletCore  # type: ignore
        core = _WalletCore()  # may accept rpc args in your impl; we use defaults if any
    except Exception:
        core = None

    if not svc and not core:
        console.print("[yellow]Wallet service not available.[/]")
        return

    def _has(obj, name):
        return hasattr(obj, name) and callable(getattr(obj, name))

    def _call(obj, name, *a, **k):
        fn = getattr(obj, name, None)
        if not callable(fn):
            return None, f"[not-supported] {name}"
        try:
            return fn(*a, **k), None
        except Exception as e:
            return None, str(e)

    def _list_wallets():
        # Try common names in order
        for name in ("list_wallets", "get_all", "list", "read_wallets"):
            if svc and _has(svc, name):
                out, err = _call(svc, name)
                return (out or []), err
        # fallback via DataLocker if WalletCore exposes it (defensive)
        if core and _has(core, "service") and hasattr(core, "service"):
            s = getattr(core, "service", None)
            if s and _has(s, "list_wallets"):
                out, err = _call(s, "list_wallets")
                return (out or []), err
        return [], None  # nothing available

    def _as_dict(w):
        # Normalize a wallet object into a dict for display
        if w is None:
            return {}
        if isinstance(w, dict):
            return w
        # Pydantic / dataclass style
        for m in ("dict", "model_dump", "__dict__"):
            if hasattr(w, m):
                try:
                    d = getattr(w, m)()
                    return dict(d)
                except Exception:
                    pass
        # Last resort
        try:
            return {k: getattr(w, k) for k in dir(w) if not k.startswith("_")}
        except Exception:
            return {"repr": repr(w)}

    def _short(addr):
        s = str(addr or "")
        return s if len(s) <= 12 else f"{s[:6]}…{s[-4:]}"

    def _render_table(wallets):
        try:
            from rich.table import Table  # type: ignore
        except Exception:
            # plain fallback
            for w in wallets:
                d = _as_dict(w)
                console.print(f"- {d.get('name') or d.get('label') or '?'} @ {_short(d.get('public_address') or d.get('address'))}  "
                              f"{'(default)' if d.get('is_default') else ''}  bal={d.get('balance')}")
            return
        table = Table(title="Wallets", expand=True)
        table.add_column("#", style="dim", width=3)
        table.add_column("Name", style="cyan")
        table.add_column("Default", width=8)
        table.add_column("Address", style="magenta")
        table.add_column("Balance", justify="right")
        for i, w in enumerate(wallets, 1):
            d = _as_dict(w)
            name = str(d.get("name") or d.get("label") or "?")
            is_def = "✅" if d.get("is_default") else ""
            addr = _short(d.get("public_address") or d.get("address"))
            bal = d.get("balance")
            bal_s = "" if bal is None else str(bal)
            table.add_row(str(i), name, is_def, addr, bal_s)
        console.print(table)

    def _input(prompt):
        try:
            return input(prompt).strip()
        except KeyboardInterrupt:
            return ""

    while True:
        wallets, err = _list_wallets()
        if err:
            console.print(f"[yellow]Note:[/] {err}")
        console.print(f"[cyan]Wallets: {len(wallets)}[/]")
        _render_table(wallets)

        console.print("\n[bold]Actions[/]: "
                      "[1] View details  "
                      "[2] Set default  "
                      "[3] Refresh balances  "
                      "[4] Import from file  "
                      "[5] Create wallet  "
                      "[6] Delete wallet  "
                      "[7] Delete ALL  "
                      "[0] Back")
        choice = _input("→ ").lower()

        if choice in ("0", "q", "back", ""):
            return

        elif choice == "1":
            idx = _input("Index or name: ")
            target = None
            if idx.isdigit() and 1 <= int(idx) <= len(wallets):
                target = wallets[int(idx) - 1]
            else:
                for w in wallets:
                    d = _as_dict(w)
                    if str(d.get("name") or d.get("label")) == idx:
                        target = w
                        break
            if not target:
                console.print("[yellow]Not found.[/]")
                continue
            d = _as_dict(target)
            # pretty print dict
            try:
                from rich import box
                from rich.panel import Panel  # type: ignore
                from rich.pretty import Pretty  # type: ignore
                console.print(Panel(Pretty(d), title=f"Wallet: {d.get('name') or '?'}", box=box.ROUNDED))
            except Exception:
                console.print(d)

        elif choice == "2":
            name = _input("Set default wallet (name): ")
            if not name:
                continue
            # Try common setters in order
            attempted = ("set_default_wallet", "set_default", "make_default")
            ok = False
            for meth in attempted:
                if svc and _has(svc, meth):
                    _, e = _call(svc, meth, name)
                    if not e:
                        console.print(f"[green]Default set: {name}[/]")
                        ok = True
                        break
            if not ok:
                console.print("[yellow]Not supported by WalletService.[/]")
                continue

        elif choice == "3":
            # Prefer WalletCore refreshers
            if core and _has(core, "refresh_wallet_balances"):
                out, e = _call(core, "refresh_wallet_balances")
                if e:
                    console.print(f"[red]Refresh failed:[/] {e}")
                else:
                    console.print(f"[green]Refreshed {out} wallet(s).[/]")
            elif svc and _has(svc, "refresh_wallet_balances"):
                out, e = _call(svc, "refresh_wallet_balances")
                if e:
                    console.print(f"[red]Refresh failed:[/] {e}")
                else:
                    console.print(f"[green]Refreshed {out} wallet(s).[/]")
            else:
                console.print("[yellow]No balance refresh method available.[/]")
            # loop continues to re-render table

        elif choice == "4":
            path = _input("File path (private key / export): ")
            if not path:
                continue
            for meth in ("import_from_file", "import_wallet_from_file", "import_wallet"):
                if svc and _has(svc, meth):
                    _, e = _call(svc, meth, path)
                    if not e:
                        console.print("[green]Imported.[/]")
                        break
            else:
                console.print("[yellow]Import not supported by WalletService.[/]")
                continue

        elif choice == "5":
            # Create wallet; prefer a ‘name’ prompt
            name = _input("New wallet name: ")
            if not name:
                continue
            for meth in ("create_wallet", "create", "new_wallet"):
                if svc and _has(svc, meth):
                    _, e = _call(svc, meth, name)
                    if not e:
                        console.print(f"[green]Created: {name}[/]")
                        break
            else:
                console.print("[yellow]Create not supported by WalletService.[/]")
                continue

        elif choice == "6":
            name = _input("Delete wallet (name): ")
            if not name:
                continue
            for meth in ("delete_wallet", "delete", "remove_wallet"):
                if svc and _has(svc, meth):
                    _, e = _call(svc, meth, name)
                    if not e:
                        console.print(f"[green]Deleted: {name}[/]")
                        break
            else:
                console.print("[yellow]Delete not supported by WalletService.[/]")
                continue

        elif choice == "7":
            sure = _input("Type YES to delete all wallets: ")
            if sure != "YES":
                continue
            for meth in ("delete_all_wallets", "delete_all"):
                if svc and _has(svc, meth):
                    _, e = _call(svc, meth)
                    if not e:
                        console.print("[green]All wallets deleted.[/]")
                        break
            else:
                console.print("[yellow]Bulk delete not supported by WalletService.[/]")
                continue

        else:
            console.print("[yellow]Unknown choice.[/]")
            continue


def goals_menu():
    try:
        from backend.models.session import Session  # type: ignore
        # Placeholder summary only; keep parity with sonic6 menu placement
        console.print(f"[cyan]Active session goals: {len(getattr(Session, 'goals', [])) if hasattr(Session,'goals') else 0}[/]")
    except Exception:
        console.print("[yellow]Session/Goals not available.[/]")


def run_daily_maintenance():
    console.print("[cyan]Running on-demand maintenance…[/]")
    # Ensure environment is sane for spec scripts before doing anything else.
    if spec_preflight is not None:
        try:
            spec_preflight(install=True)
        except Exception as _e:
            # Do not crash the UI; surface the problem as a WARN row and continue.
            print(f"[WARN] spec preflight encountered an issue: {_e}")
    else:
        print("[WARN] spec bootstrap unavailable; proceeding without preflight")
    # Hook scripts here as they become available
    console.print("[green]Done.[/]")


def banner():
    if Figlet:
        try:
            figlet = Figlet(font="slant")
            console.print(f"[bold cyan]{figlet.renderText('Sonic Launch')}[/bold cyan]")
            return
        except Exception:
            pass
    console.print("[bold cyan]Sonic Launch[/bold cyan]")


def clear_screen():
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        pass


def launch_sonic_apps():
    """Launch backend, frontend and monitor together, preferring Windows Terminal pane layout."""
    open_panes = repo_root() / "scripts" / "console" / "open_panes.bat"

    if os.name == "nt":
        if open_panes.exists():
            console.log("🪟 Launching Windows Terminal layout (Full Sonic)…")
            try:
                subprocess.run(str(open_panes), shell=True, cwd=str(repo_root()), check=False)
                console.log("[green]Windows Terminal launched. Monitor, Backend, and Frontend panes are ready.[/]")
                return
            except Exception as exc:
                console.log(f"[yellow]Windows Terminal launch failed ({exc}). Falling back to background processes.[/]")
        else:
            console.log("[yellow]scripts/console/open_panes.bat not found. Falling back to background processes.[/]")
    else:
        console.log("[yellow]Windows Terminal layout available on Windows only. Launching background processes instead.[/]")

    # Fallback to legacy triple-launch
    launch_backend()
    launch_frontend()
    launch_sonic_monitor()
    console.log("[green]Sonic Apps running with monitor in background.[/]")


# ───────────────────────── Main menu loop ─────────────────────────────────────

def _print_panel(body: str, title: str, border_style: str = "bright_magenta") -> None:
    if Panel:
        try:
            console.print(Panel.fit(body, title=title, border_style=border_style))
            return
        except Exception:
            pass
    print("\n" + body + "\n")


def main() -> None:
    while True:
        clear_screen()
        banner()
        menu_body = "\n".join(
            [
                f"1. {ICON['hog']} [bold]Full Sonic[/]",
                f"2. {ICON['rocket']} Sonic - [bold]Full App[/] (Frontend + Backend)",
                f"3. {ICON['frontend']} Launch [bold]Frontend[/] (Sonic/Vite)",
                f"4. {ICON['backend']} Launch [bold]Backend[/] (FastAPI)",
                f"5. {ICON['monitor']} Start [bold]Sonic Monitor[/]",
                f"6. {ICON['perps']} Launch Perps Console",
                f"7. {ICON['verify_db']} Verify Database",
                f"8. {ICON['tests']} Run Unit Tests",
                f"9. 🃏 Fun Console (Jokes / Quotes / Trivia)",
                f"10. {ICON['wallet']} Wallet Manager",
                f"11. {ICON['test_ui']} Test Console UI",
                f"12. {ICON['cyclone']} Launch Cyclone App",
                f"13. {ICON['goals']} Session / Goals",
                f"14. {ICON['maintenance']} On-Demand Daily Maintenance",
                f"0. {ICON['exit']} Exit   (hotkey: [C] Cyclone in a new window)",
            ]
        )
        _print_panel(menu_body, title="Main Menu")

        choice = input("→ ").strip()

        if choice == "1":
            run_menu_action("Full Sonic", launch_sonic_apps)
        elif choice == "2":
            run_menu_action("Sonic - Full App", launch_full_stack)
        elif choice == "3":
            run_menu_action("Launch Frontend (Sonic/Vite)", launch_frontend)
        elif choice == "4":
            run_menu_action("Launch Backend (FastAPI)", launch_backend)
        elif choice == "5":
            run_menu_action("Start Sonic Monitor", launch_sonic_monitor)
        elif choice == "6":
            run_menu_action("Launch Perps Console", launch_perps_console)
        elif choice == "7":
            run_menu_action("Verify Database", verify_database)
        elif choice == "8":
            run_menu_action("Run Unit Tests", run_tests)
        elif choice == "9":
            run_menu_action("Fun Console", run_fun_console)
        elif choice == "10":
            run_menu_action("Wallet Manager", wallet_menu)
        elif choice == "11":
            run_menu_action("Test Console UI", run_test_console)
        elif choice == "12":
            run_menu_action("Launch Cyclone App", launch_cyclone_app)
        elif choice == "13":
            run_menu_action("Session / Goals", goals_menu)
        elif choice == "14":
            run_menu_action("On-Demand Daily Maintenance", run_daily_maintenance)
        elif choice.upper() == "C":
            run_menu_action("Launch Cyclone App (new window)", lambda: launch_cyclone_app(new_window=True))
        elif choice in {"0", "q", "quit", "exit"}:
            print("bye 👋")
            return
        else:
            print("Invalid choice.")
            time.sleep(1.0)


if __name__ == "__main__":
    main()
