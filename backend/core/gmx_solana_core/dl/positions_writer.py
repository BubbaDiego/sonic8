from typing import List, Any
from ..models.types import NormalizedPosition

class DLWriteError(RuntimeError):
    pass

def write_positions(dl: Any, positions: List[NormalizedPosition], dry_run: bool = False) -> None:
    serial = [p.__dict__ for p in positions]
    if dry_run:
        print(f"[DL] Dry run: would write {len(serial)} normalized positions")
        return

    # Attempt common DL entry points
    try:
        from backend.data import dl_positions as dlp  # type: ignore
        if hasattr(dlp, "upsert_positions"):
            return dlp.upsert_positions(serial)  # type: ignore
    except Exception:
        pass

    if dl is not None and hasattr(dl, "upsert_positions"):
        return dl.upsert_positions(serial)  # type: ignore

    try:
        from backend.data.data_locker import DataLocker  # type: ignore
        locker = dl if dl is not None else DataLocker()
        if hasattr(locker, "write_positions"):
            return locker.write_positions(serial)  # type: ignore
    except Exception:
        pass

    raise DLWriteError("No compatible Data Locker entrypoint found. Provide dl instance or export backend.data.dl_positions.upsert_positions().")
