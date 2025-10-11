"""
Root launcher for the Sonic monitor.
Run me from repo root:  python sonic_monitor.py
This preserves proper package imports without any sys.path shim.
"""
from backend.core.monitor_core.utils.console_title import set_console_title
import backend.core.monitor_core.sonic_monitor as runner


def _run():
    # Cosmetic title; safe if it no-ops on non-Windows
    try:
        set_console_title("🌀 Sonic Monitor")
    except Exception:
        pass

    # Call the monitor’s main entry. Try 'main', else 'run_monitor'.
    if hasattr(runner, "main"):
        runner.main()
    elif hasattr(runner, "run_monitor"):
        runner.run_monitor()
    else:
        raise RuntimeError("No entrypoint found: expected runner.main() or runner.run_monitor().")


if __name__ == "__main__":
    _run()
