# -*- coding: utf-8 -*-
from __future__ import annotations
import os
from backend.data.data_locker import DataLocker
from backend.core.monitor_core.sonic.engine import MonitorEngine

def main():
    dl = DataLocker.get_instance()
    debug = (os.getenv("SONIC_DEBUG", "0").strip().lower() in {"1","true","yes","on"})
    interval = int(os.getenv("SONIC_INTERVAL_SEC", "34"))
    eng = MonitorEngine(dl=dl, cfg={}, debug=debug)
    eng.run_forever(interval_sec=interval)

if __name__ == "__main__":
    main()
