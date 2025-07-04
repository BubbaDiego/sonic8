from backend.console.cyclone_console_service import CycloneConsoleService
from backend.core.cyclone_core.cyclone_engine import Cyclone


def run_console() -> None:
    """Entry point used by Launch Pad to open the Cyclone console."""
    cyclone = Cyclone(poll_interval=60)
    helper = CycloneConsoleService(cyclone)
    helper.run_console()
