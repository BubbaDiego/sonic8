from __future__ import annotations

from pathlib import Path

from backend.core.core_imports import log  # optional logging


def reset_database(db_path: str) -> None:
    """Delete the SQLite database and associated WAL/SHM files if they exist."""
    path = Path(db_path)
    try:
        if path.exists():
            path.unlink()
            log.debug(f"Removed database file: {path}", source="reset_database")
    except Exception as e:  # pragma: no cover - best effort cleanup
        log.error(f"Failed to delete database {path}: {e}", source="reset_database")
    for suffix in ("-wal", "-shm"):
        extra = Path(f"{db_path}{suffix}")
        try:
            if extra.exists():
                extra.unlink()
                log.debug(f"Removed database file: {extra}", source="reset_database")
        except Exception as e:  # pragma: no cover - best effort cleanup
            log.error(f"Failed to delete {extra}: {e}", source="reset_database")
