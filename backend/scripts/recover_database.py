#!/usr/bin/env python3
"""Recover and reinitialize the SQLite database.

This script deletes the existing database file if it is corrupt, recreates
all required tables and seeds any default data. It mirrors the **Recover
Database** option from the interactive menu.
"""
from __future__ import annotations

from core.core_constants import MOTHER_DB_PATH
from core.logging import configure_console_log
from data.data_locker import DataLocker


def main() -> int:
    """Perform recovery and initialization."""
    configure_console_log()
    locker = DataLocker(str(MOTHER_DB_PATH))
    locker.db.recover_database()
    locker.initialize_database()
    locker._seed_modifiers_if_empty()
    locker._seed_wallets_if_empty()
    locker._seed_thresholds_if_empty()
    locker.close()
    print(f"\u2705 Database recovery complete: {MOTHER_DB_PATH}")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual execution
    raise SystemExit(main())
