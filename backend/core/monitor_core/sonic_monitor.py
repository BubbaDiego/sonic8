# -*- coding: utf-8 -*-
from __future__ import annotations
import os
from backend.data.data_locker import DataLocker
from backend.core.monitor_core.sonic.engine import MonitorEngine

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
    debug = (os.getenv("SONIC_DEBUG", "0").strip().lower() in {"1","true","yes","on"})
    interval = int(os.getenv("SONIC_INTERVAL_SEC", "34"))

    # BEGIN CODEX: webterm external launcher (script) — prefers script, falls back to prior autostart if any
    _launched = False
    if _webterm_launch_script:
        try:
            logger_obj = globals().get("logger", None)
            pid = _webterm_launch_script(logger=logger_obj)
            _launched = bool(pid)
            if _launched:
                msg = f"[WebTerm] launcher script started (PID={pid}). See reports\\webterm_launcher.log"
                if logger_obj:
                    try:
                        logger_obj.info(msg)
                    except Exception:
                        print(msg)
                else:
                    print(msg)
        except Exception as _e:
            logger_obj = globals().get("logger", None)
            if logger_obj:
                try:
                    logger_obj.warning(f"[WebTerm] launcher script failed: {_e}")
                except Exception:
                    print(f"[WebTerm] launcher script failed: {_e}")
            else:
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
