# -*- coding: utf-8 -*-
from __future__ import annotations
import os
from backend.data.data_locker import DataLocker
from backend.core.monitor_core.sonic.engine import MonitorEngine

# BEGIN CODEX: webterm imports
try:
    from backend.core.webterm_core.autostart import autostart as webterm_autostart
except Exception:
    webterm_autostart = None
# END CODEX

def main():
    dl = DataLocker.get_instance()
    debug = (os.getenv("SONIC_DEBUG", "0").strip().lower() in {"1","true","yes","on"})
    interval = int(os.getenv("SONIC_INTERVAL_SEC", "34"))

    # BEGIN CODEX: webterm autostart
    if webterm_autostart:
        try:
            webterm_autostart(dl)  # prints link at startup; persists state in dl.system["webterm"]
        except Exception as _e:
            # keep Sonic alive even if webterm fails
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
