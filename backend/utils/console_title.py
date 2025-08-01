import os
import sys
import ctypes


def set_console_title(title: str) -> None:
    """Best-effort set of the terminal window title."""
    if os.getenv("NO_CONSOLE_TITLE") == "1":
        return
    try:
        if os.name == "nt":
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        else:
            sys.stdout.write(f"\x1b]0;{title}\x07")
            sys.stdout.flush()
    except Exception:
        pass


__all__ = ["set_console_title"]
