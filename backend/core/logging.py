"""Simple console logging utilities."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict


class SimpleLogger:
    """Very small wrapper around :mod:`logging` used across the project."""

    def __init__(self) -> None:
        self._logger = logging.getLogger("sonic1")
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
        self._timers: Dict[str, datetime] = {}
        self.configure()

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    def configure(self, level: int = logging.INFO) -> None:
        self._logger.setLevel(level)

    # ------------------------------------------------------------------
    # Basic logging methods
    # ------------------------------------------------------------------
    def debug(
        self,
        msg: str,
        source: str | None = None,
        payload: Any | None = None,
        **_: Any,
    ) -> None:
        self._logger.debug(self._format(msg, source, payload))

    def info(
        self,
        msg: str,
        source: str | None = None,
        payload: Any | None = None,
        **_: Any,
    ) -> None:
        self._logger.info(self._format(msg, source, payload))

    def warning(
        self,
        msg: str,
        source: str | None = None,
        payload: Any | None = None,
        **_: Any,
    ) -> None:
        self._logger.warning(self._format(msg, source, payload))

    def error(
        self,
        msg: str,
        source: str | None = None,
        payload: Any | None = None,
        **_: Any,
    ) -> None:
        self._logger.error(self._format(msg, source, payload))

    # Convenience aliases ------------------------------------------------
    def success(
        self,
        msg: str,
        source: str | None = None,
        payload: Any | None = None,
        **_: Any,
    ) -> None:
        self._logger.info(self._format(msg, source, payload))

    def banner(
        self,
        msg: str,
        source: str | None = None,
        payload: Any | None = None,
        **_: Any,
    ) -> None:
        banner_msg = f"==== {msg} ===="
        self._logger.info(self._format(banner_msg, source, payload))

    def route(
        self,
        msg: str,
        source: str | None = None,
        payload: Any | None = None,
        **_: Any,
    ) -> None:
        """Log a route access message using :meth:`info`."""
        self._logger.info(self._format(msg, source, payload))

    # ------------------------------------------------------------------
    # Timer helpers
    # ------------------------------------------------------------------
    def start_timer(self, name: str) -> None:
        self._timers[name] = datetime.now()

    def end_timer(self, name: str, source: str | None = None) -> None:
        start = self._timers.pop(name, None)
        if start:
            elapsed = datetime.now() - start
            self._logger.info(self._format(f"{name} completed in {elapsed}", source))

    # ------------------------------------------------------------------
    # No-op compatibility helpers
    # ------------------------------------------------------------------
    def assign_group(self, *_: Any, **__: Any) -> None:
        pass

    def enable_group(self, *_: Any, **__: Any) -> None:
        pass

    def silence_module(self, *_: Any, **__: Any) -> None:
        pass

    def hijack_logger(self, *_: Any, **__: Any) -> None:
        pass

    def init_status(self, *_: Any, **__: Any) -> None:
        pass

    def txt(self, *_: Any, **__: Any) -> None:
        pass


    # Compatibility helpers -------------------------------------------------
    def print_dashboard_link(
        self, host: str = "127.0.0.1", port: int = 5001, route: str = "/dashboard"
    ) -> None:
        """Print a simple dashboard URL."""
        url = f"http://{host}:{port}{route}"

        self.info(f"🌐 Sonic Dashboard: {url}")


    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _format(self, msg: str, source: str | None, payload: Any | None = None) -> str:
        base = f"[{source}] {msg}" if source else msg
        if payload is not None:
            base = f"{base} {payload}"
        return base


# Public API ---------------------------------------------------------------
log = SimpleLogger()


def configure_console_log(debug: bool = False) -> None:
    """Configure the console logger."""
    level = logging.DEBUG if debug else logging.INFO
    log.configure(level)


__all__ = ["log", "configure_console_log"]
