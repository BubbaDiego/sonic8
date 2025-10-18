from __future__ import annotations
import os
from pathlib import Path
from typing import Tuple


def resolve_mother_db_path() -> Tuple[Path, str]:
    """
    Resolve mother.db path with provenance.
    Prefers env MOTHER_DB_PATH, else <repo>/backend/mother.db.
    Returns (path, provenance) where provenance is 'ENV' or 'DEFAULT'.
    """
    env = os.getenv("MOTHER_DB_PATH")
    if env:
        return Path(env).expanduser().resolve(), "ENV"
    # path_utils.py is under backend/core/common → repo_root = parents[3]
    repo_root = Path(__file__).resolve().parents[3]
    return (repo_root / "backend" / "mother.db").resolve(), "DEFAULT"


def is_under_repo(p: Path) -> bool:
    repo_root = Path(__file__).resolve().parents[3]
    try:
        p.resolve().relative_to(repo_root)
        return True
    except Exception:
        return False
