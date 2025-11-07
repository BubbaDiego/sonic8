from __future__ import annotations

# Back-compat wrapper: older callers import run_console(); new code can import
# run_cyclone_console directly from cyclone_console_service.

from .cyclone_console_service import run_cyclone_console

def run_console() -> None:
    run_cyclone_console()

if __name__ == "__main__":
    run_cyclone_console()
