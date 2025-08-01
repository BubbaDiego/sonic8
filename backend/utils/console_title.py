import os
import sys


def set_console_title(title: str) -> None:
    """Set the terminal window title if supported."""
    try:
        if os.name == "nt":
            os.system(f"title {title}")
        else:
            sys.stdout.write(f"\33]0;{title}\a")
            sys.stdout.flush()
    except Exception:
        pass
