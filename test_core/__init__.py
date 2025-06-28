from .test_core import TestCore, TestCoreConsole

def get_console_ui():
    from .console_ui import TestConsoleUI
    return TestConsoleUI

__all__ = ["TestCore", "TestCoreConsole", "get_console_ui"]
