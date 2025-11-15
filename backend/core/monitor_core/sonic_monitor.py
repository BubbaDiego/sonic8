# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path  # BEGIN CODEX: new import

from backend.data.data_locker import DataLocker
from backend.core.monitor_core.sonic.engine import MonitorEngine
from backend.core.monitor_core.utils.banner import emit_config_banner  # BEGIN CODEX: new import

try:
    from backend.core.webterm_core.autostart import autostart as webterm_autostart
except Exception:
    webterm_autostart = None

try:
    from backend.core.webterm_core.script_launcher import launch_from_config as _webterm_launch_script
except Exception:
    _webterm_launch_script = None

def main():
    dl = DataLocker.get_instance()
    debug = (os.getenv("SONIC_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"})
    interval = int(os.getenv("SONIC_INTERVAL_SEC", "34"))

    # BEGIN CODEX: startup config banner (env + config + DB)
    try:
        # Derive repo root from this file:
        # backend/core/monitor_core/sonic_monitor.py → parents[3] = C:\\sonic8
        repo_root = Path(__file__).resolve().parents[3]
        env_path = (repo_root / ".env")
        # Use resolved path, even if the file is missing, so the banner still shows *where*
        env_path_str = str(env_path.resolve())

        # db_path_hint is informational only; emit_config_banner internally resolves mother.db
        emit_config_banner(env_path=env_path_str, db_path_hint="mother.db", dl=dl)
    except Exception as _e:
        # Keep any banner failure from breaking the monitor
        try:
            print(f"[banner] failed to emit config banner: {_e}")
        except Exception:
            pass
    # END CODEX: startup config banner

    # BEGIN CODEX: webterm external launcher (script) — prefers script, falls back to prior autostart if any
    _launched = False
    if _webterm_launch_script:
        try:
            pid = _webterm_launch_script(logger=globals().get("logger", None))
            _launched = bool(pid)
            if _launched:
                msg = f"[WebTerm] launcher script started (PID={pid}). See reports\\webterm_launcher.log"
                try:
                    logger.info(msg)  # type: ignore[name-defined]
                except Exception:
                    print(msg)
        except Exception as _e:
            try:
                logger.warning(f"[WebTerm] launcher script failed: {_e}")  # type: ignore[name-defined]
            except Exception:
                print(f"[WebTerm] launcher script failed: {_e}")

    if not _launched and webterm_autostart:
        try:
            webterm_autostart(dl)  # prints the link and persists state
        except Exception as _e:
            try:
                logger = globals().get("logger", None)
                (logger or print)(f"[WebTerm] autostart failed: {_e}")
            except Exception:
                pass
    # END CODEX

    eng = MonitorEngine(dl=dl, cfg={}, debug=debug)
    eng.run_forever(interval_sec=interval)

if __name__ == "__main__":
    main()
