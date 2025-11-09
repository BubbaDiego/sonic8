# backend/core/webterm_core/script_launcher.py
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import logging
import platform
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

IS_WINDOWS = platform.system().lower().startswith("win")

CONFIG_PATH = Path("backend/config/webterm_config.json")
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LAUNCH_LOG  = REPORTS_DIR / "webterm_launcher.log"

# Windows detached flags
CREATE_NO_WINDOW        = 0x08000000 if IS_WINDOWS else 0
DETACHED_PROCESS        = 0x00000008 if IS_WINDOWS else 0
CREATE_NEW_PROCESS_GROUP= 0x00000200 if IS_WINDOWS else 0

def _load_cfg() -> Dict[str, Any]:
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _choose_powershell() -> Optional[str]:
    """Prefer pwsh (PS7), fall back to Windows PowerShell."""
    if not IS_WINDOWS:
        return None
    pwsh = r"C:\\Program Files\\PowerShell\\7\\pwsh.exe"
    ps5  = r"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
    return pwsh if Path(pwsh).exists() else (ps5 if Path(ps5).exists() else None)

def _spawn_detached(cmd: list[str]) -> Optional[subprocess.Popen]:
    try:
        with LAUNCH_LOG.open("ab") as logf:
            kwargs = dict(stdout=logf, stderr=subprocess.STDOUT)
            if IS_WINDOWS:
                kwargs["creationflags"] = CREATE_NO_WINDOW | DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            return subprocess.Popen(cmd, **kwargs)  # noqa: S603,S607
    except Exception:
        return None

def launch_from_config(logger: Optional[logging.Logger] = None) -> Optional[int]:
    """
    If webterm_config.json has { "launcher": { "type": "script", ... } },
    start that script in a detached PowerShell and return its PID.
    """
    log = logger or logging.getLogger("webterm.launcher")
    cfg = _load_cfg()
    launcher = (cfg.get("launcher") or {})
    if str(launcher.get("type", "")).lower() != "script":
        return None

    script_path = launcher.get("path")
    args_str    = launcher.get("args", "")
    wait_ms     = int(launcher.get("wait_ms", 0) or 0)

    if not script_path or not Path(script_path).exists():
        log.warning("[WebTerm] Script path missing or not found: %r", script_path)
        return None

    ps = _choose_powershell()
    if not ps:
        log.warning("[WebTerm] PowerShell not found; cannot launch script.")
        return None

    # Build: powershell -NoProfile -ExecutionPolicy Bypass -File "script.ps1" <args...>
    cmd = [ps, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script_path]
    # Split args using Windows rules (quotes respected)
    if args_str:
        try:
            cmd += shlex.split(args_str, posix=False)
        except Exception:
            # Fallback: feed the whole string as one arg (PowerShell will treat as a single token)
            cmd.append(args_str)

    # Write a tiny preface to the log for traceability
    try:
        with LAUNCH_LOG.open("ab") as logf:
            preface = f"\n=== webterm_up: launching ===\ncmd: {' '.join(cmd)}\n"
            logf.write(preface.encode("utf-8", "ignore"))
    except Exception:
        pass

    proc = _spawn_detached(cmd)
    if not proc:
        log.error("[WebTerm] Failed to start external launcher.")
        return None

    if wait_ms > 0:
        # best-effort pause so the script can print the URL before Sonic continues
        try:
            import time
            time.sleep(wait_ms / 1000.0)
        except Exception:
            pass

    log.info("[WebTerm] External launcher started (PID=%s). Log: %s", getattr(proc, "pid", None), LAUNCH_LOG)
    return getattr(proc, "pid", None)
