from fastapi import APIRouter, Depends, HTTPException
from backend.data.data_locker import DataLocker

router = APIRouter(prefix="/db_admin", tags=["db_admin"])


def _dl() -> DataLocker:
    return DataLocker.get_instance()


@router.get("/tables", response_model=list[str])
def list_tables(dl: DataLocker = Depends(_dl)):
    return dl.db.list_tables()


@router.get("/tables/{table}", response_model=list[dict])
def read_table(table: str, limit: int = 200, dl: DataLocker = Depends(_dl)):
    try:
        return dl.read_table(table, limit)
    except Exception as exc:  # pragma: no cover - unexpected
        raise HTTPException(500, "Read failed") from exc
