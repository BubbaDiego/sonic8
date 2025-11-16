#!/usr/bin/env python3
"""
🌀 Sonic Launch Pad (sonic8)
Feature-parity with sonic6: venv re-exec, menu order, background launches,
and optional integrations (Perps, Cyclone, Fun Console, Wallet UI).
"""

from __future__ import annotations

import argparse
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
import importlib.util
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Sequence, Optional, Dict

# Windows creation flags
CREATE_NEW_CONSOLE = 0x00000010
DETACHED_PROCESS = 0x00000008  # fallback if needed

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

from backend.console.cyclone_console_service import run_cyclone_console
from backend.console.database_console_service import run_database_console
from backend.console.db_console_service import run_db_console  # use entry with db_path
# Do NOT import the config console at module import time; import lazily so we can show inline errors.


def _launch_config_console_inprocess() -> int:
    """
    Run the Config Console in the same window.
    Show a clear inline reason if it's not available (no log-only behavior).
    """

    try:
        # Lazy import so missing files surface as a readable message.
        from backend.console.config_console_service import run_config_console
    except Exception as e:
        console.print(f"[bold red]Config Console not available:[/bold red] {e}")
        console.print("Expect: backend/console/config_console_service.py with run_config_console()")
        console.print("Fix: ensure config_core + config_console files are in place, then try again.")
        return 1

    try:
        run_config_console()  # runs synchronously in this window
        return 0
    except Exception as e:
        console.print(f"[bold red]Config Console crashed:[/bold red] {e}")
        return 2
try:
    from backend.data.data_locker import DataLocker  # type: ignore
except Exception:  # pragma: no cover - optional dependency at runtime
    DataLocker = None  # type: ignore
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
    "xcom": "📞",
    "tests": "🧪",
    "topic": "🔎",
    "wallet": "💼",
    "cyclone": "🌀",
    "test_ui": "🧪🖥️",
    "perps": "🛰️",
    "goals": "🎯",
    "maintenance": "🧹",
    "exit": "⏻",
    "gmx": "🪙",
    "raydium": "💎",
    "config": "🧩",
    "market": "📈",
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


# DB Console ---------------------------------------------------------------

def _launch_db_console() -> None:
    """Launch the DB console with a path sourced from DataLocker when available."""
    db_path = None
    if 'DataLocker' in globals() and DataLocker is not None:
        try:
            locker = DataLocker.get_instance()
            db_path = getattr(getattr(locker, "db", None), "db_path", None)
        except Exception:
            db_path = None
    run_db_console(db_path)


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


def launch_gmx_solana():
    """
    Launch GMX-Solana console in a NEW window so it doesn't share stdin/stdout
    with the Launch Pad. Tries .cmd → .ps1 → python module fallback.
    """
    # 1) .cmd shim: start a new console window
    cmd_shim = Path(r"C:\\sonic8\\gmx_solana_console.cmd")
    if cmd_shim.exists():
        try:
            # Use cmd /c start "" "<path>" to spawn a new window
            subprocess.Popen(
                ["cmd", "/c", "start", "", str(cmd_shim)],
                shell=False
            )
            print("Launched GMX-Solana console via .cmd (new window)")
            return
        except Exception as e:
            print(f"Note: .cmd launch failed: {e}")

    # 2) .ps1 launcher: also new console window
    ps1 = Path(r"C:\\sonic8\\gmx_solana_console.ps1")
    if ps1.exists():
        try:
            # Start a new PowerShell window using cmd /c start
            subprocess.Popen(
                ["cmd", "/c", "start", "", "powershell", "-NoExit",
                 "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
                shell=False
            )
            print("Launched GMX-Solana console via .ps1 (new window)")
            return
        except Exception as e:
            print(f"Note: .ps1 launch failed: {e}")

    # 3) Python module fallback: force a NEW console
    try:
        repo = Path(r"C:\\sonic8")
        if repo.exists():
            env = os.environ.copy()
            env["PYTHONPATH"] = r"C:\\sonic8" + os.pathsep + env.get("PYTHONPATH", "")
            py = sys.executable or "python"
            subprocess.Popen(
                [py, "-m", "backend.core.gmx_solana_core.console.menu_console"],
                cwd=str(repo),
                env=env,
                creationflags=CREATE_NEW_CONSOLE,
                shell=False,
            )
            print("Launched GMX-Solana console via python module (new window)")
            return
        else:
            print("C:\\sonic8 not found; cannot launch GMX-Solana console.")
    except Exception as e:
        print(f"GMX-Solana launch failed: {e}")


def launch_raydium_console(new_window: bool = True) -> int:
    """
    Launch the Raydium pick-list console (wallet + NFTs).
    Uses root signer.txt via backend.services.signer_loader.
    """
    script = repo_root() / "backend" / "core" / "raydium_core" / "console" / "raydium_console.py"
    if not script.exists():
        print(f"[Raydium] Console not found: {script}")
        return 1

    # Favor a new window so stdin/stdout don't collide with Launch Pad
    return run_in_console(
        [PYTHON_EXEC, str(script)],
        cwd=repo_root(),
        title="Raydium Console",
        new_window=new_window,
    )


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


def launch_market_console(new_window: bool = True) -> int:
    """Launch the Market Core console."""

    console.print("\n[bold cyan][Market][/bold cyan] Launching Market Core Console…\n")
    cmd = [PYTHON_EXEC, "-m", "backend.console.market_console_service"]
    return run_in_console(cmd, cwd=repo_root(), title="Market Console", new_window=new_window)


def launch_cyclone_app(new_window: bool = True) -> int:
    """Launch the interactive Cyclone console (menu-driven)."""
    cmd = [PYTHON_EXEC, "-m", "backend.console.cyclone_console_service"]
    print("[Cyclone] Launching Cyclone console module…")
    return run_in_console(cmd, cwd=repo_root(), title="Cyclone App", new_window=new_window)


def run_tests_hub() -> None:
    console.log("🧪 Launching Tests Hub…")
    script = ROOT_DIR / "backend" / "scripts" / "tests_hub.py"
    if not script.exists():
        console.print("[yellow]backend/scripts/tests_hub.py not found.[/]")
        return
    try:
        run_in_console([PYTHON_EXEC, str(script)], cwd=repo_root(), title="Tests Hub")
    except Exception as exc:
        console.print(f"[yellow]Tests Hub unavailable ({exc}).[/]")


# Backwards compatibility for existing automation expecting run_tests()
def run_tests() -> None:  # pragma: no cover - shim
    run_tests_hub()

def run_test_console():
    try:
        from test_core import get_console_ui  # type: ignore
        TestConsoleUI = get_console_ui()
        TestConsoleUI().start()
    except Exception:
        console.print("[yellow]Test Console UI not available.[/]")


def _has_module(dotted: str) -> bool:
    """Return True if a module path is importable (without importing it)."""

    try:
        return importlib.util.find_spec(dotted) is not None
    except Exception:
        return False


def run_fun_console() -> None:
    """
    Robust launch for the Fun Console.
    Prefers fun_console; falls back to console or package __main__.
    Respects SONIC_FUN_CONSOLE_MOD if you want to force a module.
    """

    override = os.environ.get("SONIC_FUN_CONSOLE_MOD", "").strip()
    candidates = [
        override,
        "backend.core.fun_core.fun_console",  # ← prefer this (per sonic6 refactor)
        "backend.core.fun_core.console",      # legacy name
        "backend.core.fun_core",              # package __main__
    ]
    search = [m for m in candidates if m]

    log_dir = Path("reports/launchpad_logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"Fun_Console_{time.strftime('%Y%m%d_%H%M%S')}.log"

    target = next((m for m in search if _has_module(m)), None)
    if not target:
        msg = "Fun Console module not found. Tried: " + ", ".join(search)
        print(msg)
        log_path.write_text(msg, encoding="utf-8")
        return

    print(f"Launching Fun Console via: {target}")
    try:
        subprocess.run([sys.executable, "-m", target], check=False)
    except Exception as e:
        err = f"Fun Console failed: {e!r}"
        print(err)
        log_path.write_text(err, encoding="utf-8")


def _get_dl_manager():
    candidates = [
        ("backend.data.dl_wallets", "DLWalletManager"),
        ("backend.core.wallet_core.dl_wallet_manager", "DLWalletManager"),
        ("backend.core.data_locker.dl_wallet_manager", "DLWalletManager"),
        ("backend.core.data_locker.wallet_manager", "DLWalletManager"),
    ]
    for module_name, symbol in candidates:
        try:
            module = importlib.import_module(module_name)
            manager = getattr(module, symbol, None)
            if manager is None:
                continue
            if callable(manager):
                try:
                    return manager()
                except Exception:
                    return manager
            return manager
        except Exception:
            continue
    return None


def wallet_menu():
    """Interactive, capability-aware Wallet Manager (works with whatever wallet_core provides)."""
    # Lazy imports; we don't assume all modules exist in sonic8
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

    dl = _get_dl_manager()

    if not svc and not core and not dl:
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
        except TypeError as e:
            if len(a) == 1 and isinstance(a[0], dict) and not k:
                try:
                    return fn(**a[0]), None
                except Exception as inner:
                    return None, str(inner)
            return None, str(e)
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
        if dl and _has(dl, "list_wallets"):
            out, err = _call(dl, "list_wallets")
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
            # Create wallet; prompt for key fields
            name = _input("New wallet name: ")
            pub = _input("Public address: ")
            img = _input("Image path or URL (e.g., /static/images/vader.jpg): ")
            if not name or not pub:
                console.print("[yellow]Name and public address are required.[/]")
                continue

            payload_dict = {
                "name": name,
                "public_address": pub,
                "image_path": img or None,
            }
            payload_obj = payload_dict
            try:
                from backend.core.wallet_core.wallet_schema import WalletIn  # type: ignore

                payload_obj = WalletIn(**payload_dict)  # type: ignore[assignment]
            except Exception:
                pass

            created = False
            last_err = None
            for meth in ("create_wallet", "create", "add_wallet", "new_wallet"):
                if svc and _has(svc, meth):
                    _, last_err = _call(svc, meth, payload_obj)
                    if not last_err:
                        created = True
                    break

            if not created and dl:
                for meth in ("create_wallet", "create", "add_wallet", "add"):
                    if _has(dl, meth):
                        _, last_err = _call(dl, meth, payload_dict)
                        if not last_err:
                            created = True
                        break

            if created:
                console.print(f"[green]Created: {name}[/]")
            else:
                if last_err:
                    console.print(f"[yellow]{last_err}[/]")
                console.print("[yellow]Create not supported by WalletService/DLWalletManager.[/]")
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

    # ── helper to run a single Python script with capture ───────────────────
    def _run_spec_step(title: str, relpath: str, *args: str) -> int | None:
        script = (repo_root() / relpath)
        if not script.exists():
            print(f"{title:<32} [skip] {relpath} not found")
            return None
        print(f"{title:<32} [run]  {relpath}")
        env = os.environ.copy()
        # Ensure Python uses UTF-8 for stdio to avoid cp1252 UnicodeEncodeError in child scripts
        env.setdefault("PYTHONIOENCODING", "utf-8")
        # capture output to keep it in the action log and on screen
        proc = subprocess.run(
            [PYTHON_EXEC, str(script), *args],
            cwd=str(repo_root()),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=False,
        )
        if proc.stdout:
            print(proc.stdout)
        if proc.stderr:
            print(proc.stderr)
        status = "ok" if proc.returncode == 0 else f"fail({proc.returncode})"
        print(f"{title:<32} [{status}]")
        return proc.returncode

    # ── run available steps (exists-check protects sonic8 state) ────────────
    results = []
    results.append(_run_spec_step("Export OpenAPI",            "backend/scripts/export_openapi.py"))
    results.append(_run_spec_step("Build UI Components doc",   "backend/scripts/build_ui_components_doc.py"))
    results.append(_run_spec_step("Build Schema Bundle",       "backend/scripts/build_schema_bundle.py"))
    results.append(_run_spec_step("Validate ALL specs",        "backend/scripts/validate_all_specs.py"))

    ok   = sum(1 for r in results if r == 0)
    fail = sum(1 for r in results if isinstance(r, int) and r != 0)
    skip = sum(1 for r in results if r is None)
    print(f"\nSummary → ok={ok}  fail={fail}  skip={skip}")
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


def launch_full_sonic_uno() -> None:
    console.log("🦔 Launching Full Sonic – Uno layout…")
    if os.name != "nt":
        console.log("[yellow]Full Sonic – Uno requires Windows. Launching legacy Full Sonic instead.[/]")
        launch_sonic_apps()
        return

    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:
        console.log("[yellow]PowerShell not found. Launching legacy Full Sonic instead.[/]")
        launch_sonic_apps()
        return

    uno_script = repo_root() / "scripts" / "full_sonic_uno.ps1"
    if not uno_script.exists():
        console.log("[yellow]scripts/full_sonic_uno.ps1 not found. Launching legacy Full Sonic instead.[/]")
        launch_sonic_apps()
        return

    try:
        subprocess.Popen(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(uno_script),
            ],
            cwd=str(repo_root()),
        )
        console.log("[green]Windows Terminal Uno layout launching. Panes will open shortly.[/]")
    except Exception as exc:
        console.log(f"[yellow]Full Sonic – Uno launch failed ({exc}). Launching legacy Full Sonic instead.[/]")
        launch_sonic_apps()


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
                "1. 🌀 Start [bold]Sonic Monitor[/]",
                f"2. {ICON['hog']} [bold]Full Sonic[/]",
                f"3. {ICON['hog']} [bold]Full Sonic – Uno[/] (single window, split panes)",
                f"4. {ICON['rocket']} Sonic - [bold]Full App[/] (Frontend + Backend)",
                f"5. {ICON['frontend']} Launch [bold]Frontend[/] (Sonic/Vite)",
                f"6. {ICON['backend']} Launch [bold]Backend[/] (FastAPI)",
                f"7. {ICON['verify_db']} Database Console",
                f"8. {ICON['config']} Config Console",
                f"9. {ICON['tests']} Tests Hub",
                f"10. 🃏 Fun Console (Jokes / Quotes / Trivia)",
                f"11. {ICON['wallet']} Wallet Manager",
                f"12. {ICON['cyclone']} Launch Cyclone App",
                f"13. {ICON['goals']} Session / Goals",
                f"14. {ICON['maintenance']} On-Demand Daily Maintenance",
                f"15. {ICON['gmx']} GMX Solana Console",
                f"16. {ICON['raydium']} Raydium Console (wallet + NFTs)",
                f"17. {ICON['xcom']} Seed XCom Providers (ENV)",
                f"18. {ICON['market']} Market Console (Market Core)",
                f"0. {ICON['exit']} Exit   (hotkey: [S] Sonic Monitor, [C] Cyclone Console, [D] Database Console, [G] Config Console, [M] Market Console)",
            ]
        )
        _print_panel(menu_body, title="Main Menu")

        choice = input("→ ").strip()

        if choice == "1" or choice.upper() == "S":
            run_menu_action("🌀 Start Sonic Monitor", launch_sonic_monitor)
        elif choice == "2":
            run_menu_action("Full Sonic", launch_sonic_apps)
        elif choice == "3":
            run_menu_action("Full Sonic – Uno", launch_full_sonic_uno)
        elif choice == "4":
            run_menu_action("Sonic - Full App", launch_full_stack)
        elif choice == "5":
            run_menu_action("Launch Frontend (Sonic/Vite)", launch_frontend)
        elif choice == "6":
            run_menu_action("Launch Backend (FastAPI)", launch_backend)
        elif choice == "7":
            run_menu_action("Database Console", _launch_db_console)
        elif choice == "8":
            run_menu_action("Config Console", _launch_config_console_inprocess)
        elif choice == "9":
            run_menu_action("Tests Hub", run_tests_hub)
        elif choice == "10":
            run_menu_action("Fun Console", run_fun_console)
        elif choice == "11":
            run_menu_action("Wallet Manager", wallet_menu)
        elif choice == "12":
            run_menu_action("Launch Cyclone App", run_cyclone_console)
        elif choice == "13":
            run_menu_action("Session / Goals", goals_menu)
        elif choice == "14":
            run_menu_action("On-Demand Daily Maintenance", run_daily_maintenance)
        elif choice == "15":
            run_menu_action("GMX Solana Console", launch_gmx_solana)
        elif choice == "16":
            run_menu_action("Raydium Console", launch_raydium_console)
        elif choice == "17":
            run_menu_action("Seed XCom Providers", run_database_console)
        elif choice == "18":
            run_menu_action("Market Console", launch_market_console)
        elif choice.upper() == "D":
            run_menu_action("Database Console", _launch_db_console)
        elif choice.upper() == "G":
            run_menu_action("Config Console", _launch_config_console_inprocess)
        elif choice.upper() == "C":
            run_menu_action("Cyclone Console", lambda: launch_cyclone_app(new_window=True))
        elif choice.upper() == "M":
            run_menu_action("Market Console", launch_market_console)
        elif choice in {"0", "q", "quit", "exit"}:
            print("bye 👋")
            return
        else:
            print("Invalid choice.")
            time.sleep(1.0)



def cli_entry(argv: Optional[Sequence[str]] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        main()
        return

    parser = argparse.ArgumentParser(prog='launch-pad', description='Sonic Launch Pad utilities')
    sub = parser.add_subparsers(dest='cmd')

    t = sub.add_parser('test', help='Run tests by topic/bundle with reports')
    t.add_argument('--topic', action='append', help='Topic keyword; repeatable.')
    t.add_argument('--bundle', action='append', default=[], help='Bundle from test_core/topics.yaml; repeatable.')
    t.add_argument(
        '--path',
        action='append',
        default=['test_core/tests', 'tests'],
        help='Discovery roots; default=test_core/tests, tests',
    )
    t.add_argument('--fuzzy', type=int, default=75, help='Fuzzy threshold (0-100).')
    t.add_argument('--exclude', action='append', default=[], help='Exclude keywords joined in a NOT clause.')
    t.add_argument('--parallel', type=int, default=0, help='pytest-xdist workers; 0 disables.')
    t.add_argument('--maxfail', type=int, default=1, help='Abort after N failures.')
    t.add_argument('--show', action='store_true', help='Show selected nodeids before running.')
    t.add_argument('--dry-run', action='store_true', help='Collect and show selection, then exit.')
    t.add_argument('--quiet', action='store_true', help='Pass -q to pytest.')
    t.add_argument('--junit-prefix', default='topic', help='Prefix for JUnit filename.')

    args = parser.parse_args(argv)

    if args.cmd == 'test':
        from test_core.topic_console import main as topic_main
        topic_argv: list[str] = []
        for value in args.topic or []:
            topic_argv += ['--topic', value]
        for value in args.bundle or []:
            topic_argv += ['--bundle', value]
        for value in args.path or []:
            topic_argv += ['--path', value]
        for value in args.exclude:
            topic_argv += ['--exclude', value]
        topic_argv += [
            '--fuzzy', str(args.fuzzy),
            '--parallel', str(args.parallel),
            '--maxfail', str(args.maxfail),
            '--junit-prefix', args.junit_prefix,
        ]
        if args.show:
            topic_argv.append('--show')
        if args.dry_run:
            topic_argv.append('--dry-run')
        if args.quiet:
            topic_argv.append('--quiet')
        raise SystemExit(topic_main(topic_argv))

    parser.print_help()


if __name__ == "__main__":
    cli_entry()
