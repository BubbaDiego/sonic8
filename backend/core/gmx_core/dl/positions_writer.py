from typing import List, Any

from ..services.position_source import NormalizedPosition

class DLWriteError(RuntimeError):
    pass

def write_positions(dl: Any, positions: List[NormalizedPosition], dry_run: bool = False) -> None:
    """
    Integrates with sonic7 Data Locker layer.

    We try a few conventional entrypoints to avoid tight coupling:
      1) backend.data.dl_positions.upsert_positions(list[dict])
      2) dl.upsert_positions(list[dict]) if a DL instance is passed in
      3) backend.data.data_locker.DataLocker().write_positions(...)

    Codex: if your DL surface is different, add a thin adapter there or tweak this writer.
    """
    serial = [p.__dict__ for p in positions]

    if dry_run:
        print(f"[DL] Dry run: would write {len(serial)} normalized positions")
        return

    # Strategy 1: module function
    try:
        from backend.data import dl_positions as dlp  # type: ignore
        if hasattr(dlp, "upsert_positions"):
            return dlp.upsert_positions(serial)  # type: ignore
    except Exception:
        pass

    # Strategy 2: object method
    if dl is not None and hasattr(dl, "upsert_positions"):
        return dl.upsert_positions(serial)  # type: ignore

    # Strategy 3: DataLocker class
    try:
        from backend.data.data_locker import DataLocker  # type: ignore
        locker = dl if dl is not None else DataLocker()
        if hasattr(locker, "write_positions"):
            return locker.write_positions(serial)  # type: ignore
    except Exception:
        pass

    raise DLWriteError("No compatible Data Locker entrypoint found. Provide dl instance or export backend.data.dl_positions.upsert_positions().")
