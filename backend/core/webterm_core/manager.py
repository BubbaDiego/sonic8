# SPDX-License-Identifier: MIT
"""
WebTerm Manager
---------------
Starts and supervises a local web terminal (ttyd) and an optional public tunnel
(Cloudflare named/quick or Tailscale). Persists state into DataLocker if provided,
and also into reports/webterm_state.json for easy inspection.

No external Python deps; Windows-friendly; safe to import anywhere.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shlex
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import shutil
import platform

# ---------- Helpers ----------

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
STATE_PATH = REPORTS_DIR / "webterm_state.json"
TTYD_LOG = REPORTS_DIR / "ttyd.log"
CF_LOG = REPORTS_DIR / "cloudflared.log"

IS_WINDOWS = platform.system().lower().startswith("win")

CREATE_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0
DETACHED_PROCESS = 0x00000008 if IS_WINDOWS else 0


def _which(exe: str) -> Optional[str]:
    return shutil.which(exe)


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _is_port_listening(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _sleep_until(predicate, timeout_s: float, interval_s: float = 0.25) -> bool:
    started = time.time()
    while time.time() - started < timeout_s:
        if predicate():
            return True
        time.sleep(interval_s)
    return predicate()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- DataLocker shim ----------

class _DLShim:
    """
    Best-effort adapter so we don't need to know your exact DataLocker API.
    Tries (in order):
      - dl.system.set_var(key, value)
      - dl.set_system_var(key, value)
      - dl.set_var(key, value)
    And similar for get.
    Falls back to a local JSON file if none exist.
    """
    def __init__(self, dl: Any = None):
        self.dl = dl

    def set(self, key: str, value: Any):
        if self.dl is None:
            _write_json(STATE_PATH, value)
            return
        if hasattr(self.dl, "system") and hasattr(self.dl.system, "set_var"):
            return self.dl.system.set_var(key, value)
        if hasattr(self.dl, "set_system_var"):
            return self.dl.set_system_var(key, value)
        if hasattr(self.dl, "set_var"):
            return self.dl.set_var(key, value)
        _write_json(STATE_PATH, value)

    def get(self, key: str, default: Any = None):
        if self.dl is None:
            return _read_json(STATE_PATH, default)
        if hasattr(self.dl, "system") and hasattr(self.dl.system, "get_var"):
            try:
                val = self.dl.system.get_var(key)
                return default if val is None else val
            except Exception:
                return default
        for name in ("get_system_var", "get_var"):
            if hasattr(self.dl, name):
                try:
                    return getattr(self.dl, name)(key) or default
                except Exception:
                    pass
        return default


def _write_json(path: Optional[Path], obj: Any):
    try:
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
    except Exception:
        pass


def _read_json(path: Optional[Path], default: Any = None):
    try:
        if path is None:
            return default
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


# ---------- Process helpers ----------

def _spawn(cmd: list[str], log_path: Path) -> Optional[subprocess.Popen]:
    """
    Start a long-running process in the background.
    Stdout/stderr are redirected to `log_path`.
    """
    try:
        log_f = log_path.open("ab")
        kwargs = dict(stdout=log_f, stderr=subprocess.STDOUT)
        if IS_WINDOWS:
            kwargs["creationflags"] = CREATE_NO_WINDOW | DETACHED_PROCESS
        proc = subprocess.Popen(cmd, **kwargs)  # noqa: S603,S607 (trusted bin)
        return proc
    except FileNotFoundError:
        return None
    except Exception:
        return None


# ---------- Cloudflare helpers ----------

_URL_RE = re.compile(r"https?://[A-Za-z0-9\.\-]+(?:trycloudflare\.com|\.link|\.cfargotunnel\.com|[A-Za-z0-9\.\-]+)/?", re.I)


def _parse_cloudflared_url_from_log(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        m = _URL_RE.search(text)
        return m.group(0) if m else None
    except Exception:
        return None


def _start_cloudflare_quick(local_port: int) -> Tuple[Optional[subprocess.Popen], Optional[str]]:
    exe = _which("cloudflared") or _which("cloudflared.exe")
    if not exe:
        return (None, None)

    cmd = [exe, "tunnel", "--url", f"http://127.0.0.1:{local_port}", "--no-autoupdate", "--logfile", str(CF_LOG)]
    proc = _spawn(cmd, CF_LOG)
    if not proc:
        return (None, None)

    # wait for URL to appear in log
    ok = _sleep_until(lambda: bool(_parse_cloudflared_url_from_log(CF_LOG)), timeout_s=12.0)
    url = _parse_cloudflared_url_from_log(CF_LOG) if ok else None
    return (proc, url)


def _start_cloudflare_named(tunnel_name: str) -> Optional[subprocess.Popen]:
    exe = _which("cloudflared") or _which("cloudflared.exe")
    if not exe:
        return None
    if not tunnel_name:
        return None
    cmd = [exe, "tunnel", "run", tunnel_name, "--no-autoupdate", "--logfile", str(CF_LOG)]
    return _spawn(cmd, CF_LOG)


# ---------- Tailscale helpers ----------

def _tailscale_ip() -> Optional[str]:
    exe = _which("tailscale") or _which("tailscale.exe")
    if not exe:
        return None
    try:
        out = subprocess.check_output([exe, "ip", "-4"], stderr=subprocess.DEVNULL, text=True)  # noqa: S603
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        return lines[0] if lines else None
    except Exception:
        return None


# ---------- TTYD launcher ----------

def _start_ttyd(port: int, command: str, auth_user: Optional[str], auth_pass: Optional[str]) -> Optional[subprocess.Popen]:
    exe = _which("ttyd") or _which("ttyd.exe")
    if not exe:
        return None

    args = [exe, "-p", str(port)]
    if auth_user and auth_pass:
        args += ["-c", f"{auth_user}:{auth_pass}"]

    # ttyd wants: <command> <args...> — on Windows we feed PowerShell for robustness
    if IS_WINDOWS:
        args += ["powershell.exe", "-NoLogo", "-NoExit", "-Command", command]
    else:
        # Use /bin/sh -lc "<command>" to keep semantics similar on POSIX
        args += ["/bin/sh", "-lc", command]

    return _spawn(args, TTYD_LOG)


# ---------- Public API ----------

def ensure_running(config: Dict[str, Any], dl: Any = None, logger: Optional[logging.Logger] = None) -> Optional[str]:
    """
    Idempotently ensure the web terminal and its tunnel are up.

    Returns the public (or local) URL string if available, else None.
    """
    log = logger or logging.getLogger("webterm")

    enabled = bool(config.get("enabled", True))
    if not enabled:
        return None

    provider = str(config.get("provider", "cloudflare")).lower().strip()  # cloudflare | tailscale | none
    port = int(config.get("port", 7681))
    command = config.get("command") or r"C:\\sonic7\\.venv\\Scripts\\python.exe C:\\sonic7\\launch_pad.py"

    auth_cfg = config.get("auth", {}) or {}
    auth_user = os.environ.get(auth_cfg.get("basic_user_env", "") or "")
    auth_pass = os.environ.get(auth_cfg.get("basic_pass_env", "") or "")

    # 1) Start ttyd if needed
    if not _is_port_listening(port):
        proc = _start_ttyd(port, command, auth_user, auth_pass)
        if not proc:
            log.warning("[WebTerm] ttyd not found or failed to start; skipping web terminal.")
            return None
        _sleep_until(lambda: _is_port_listening(port), timeout_s=10.0)
    else:
        log.debug("[WebTerm] ttyd already listening on port %s", port)

    # 2) Resolve URL based on provider
    url: Optional[str] = None
    tunnel_pid: Optional[int] = None
    mode = None

    if provider == "cloudflare":
        cf = config.get("cloudflare", {}) or {}
        mode = str(cf.get("mode", "named")).lower().strip()
        if mode == "named":
            # Prefer a named tunnel; URL is stable — just use the configured hostname for display.
            hostname = cf.get("hostname")
            tunnel_name = cf.get("tunnel_name") or (hostname.split(".")[0] if isinstance(hostname, str) and "." in hostname else None)
            proc = _start_cloudflare_named(tunnel_name) if tunnel_name else None
            tunnel_pid = getattr(proc, "pid", None)
            if hostname:
                url = f"https://{hostname}"
        else:
            # Quick tunnel; parse URL from log
            proc, url = _start_cloudflare_quick(port)
            tunnel_pid = getattr(proc, "pid", None)

    elif provider == "tailscale":
        ts_ip = _tailscale_ip()
        if ts_ip:
            url = f"http://{ts_ip}:{port}"
        mode = "lan"

    else:
        url = f"http://127.0.0.1:{port}"
        mode = "local"

    # 3) Persist state
    state = {
        "active": True,
        "port": port,
        "provider": provider,
        "mode": mode,
        "url": url,
        "started_at": _now_iso(),
        "ttyd_log": str(TTYD_LOG),
        "cloudflared_log": str(CF_LOG),
        "note": "If url is None for quick tunnels, inspect cloudflared log; named tunnels use configured hostname.",
    }
    dlshim = _DLShim(dl)
    dlshim.set("webterm", state)
    _write_json(STATE_PATH, state)

    return url
