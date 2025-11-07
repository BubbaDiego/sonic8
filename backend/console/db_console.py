# backend/console/db_console.py
from __future__ import annotations

from .db_console_service import run_db_console


def run_console() -> None:
    run_db_console()


if __name__ == "__main__":
    run_db_console()
