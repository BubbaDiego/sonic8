from __future__ import annotations

import os
import sys


def set_console_title(title: str) -> None:
    """Set the terminal title bar if not disabled."""
    if os.getenv("NO_CONSOLE_TITLE") == "1":
        return

    env_title = os.getenv("CONSOLE_TITLE")
    final_title = env_title if env_title else title

    try:
        sys.stdout.write(f"\033]0;{final_title}\a")
        sys.stdout.flush()
    except Exception:
        pass

    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleTitleW(str(final_title))
        except Exception:
            pass


__all__ = ["set_console_title"]
