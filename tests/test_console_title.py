import ctypes
from unittest.mock import patch, MagicMock

from backend.utils.console_title import set_console_title


def test_set_console_title_posix():
    with patch("sys.stdout.write") as write_mock, patch("sys.stdout.flush") as flush_mock:
        with patch("os.name", "posix", create=True):
            set_console_title("Hello")
        write_mock.assert_called_with("\x1b]0;Hello\x07")
        flush_mock.assert_called_once()


def test_set_console_title_windows():
    fake_kernel = MagicMock()
    with patch("os.name", "nt", create=True), patch.object(ctypes, "windll", MagicMock(kernel32=fake_kernel), create=True):
        set_console_title("Win")
    fake_kernel.SetConsoleTitleW.assert_called_with("Win")


def test_no_console_title_env(monkeypatch):
    monkeypatch.setenv("NO_CONSOLE_TITLE", "1")
    with patch("sys.stdout.write") as write_mock, patch.object(ctypes, "windll", MagicMock(kernel32=MagicMock()), create=True):
        set_console_title("Skip")
    write_mock.assert_not_called()
