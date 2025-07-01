try:  # optional - avoid heavy imports if core deps missing
    from .test_core import TestCore, TestCoreConsole
except Exception:  # pragma: no cover - fallback when core package unavailable
    TestCore = TestCoreConsole = None  # type: ignore
from .runner import TestCoreRunner

def get_console_ui():
    from .console_ui import TestConsoleUI
    return TestConsoleUI

__all__ = ["TestCore", "TestCoreConsole", "TestCoreRunner", "get_console_ui"]
