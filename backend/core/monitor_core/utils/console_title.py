import os
import sys


def set_console_title(title: str) -> None:
    """Best-effort console title setter. No-ops on failure."""
    try:
        if os.name == "nt":
            # Windows console title
            os.system(f"title {title}")
        else:
            # ANSI terminal title
            sys.stdout.write(f"\x1b]0;{title}\x07")
            sys.stdout.flush()
    except Exception:
        # Don't ever crash the monitor over cosmetics
        pass
