from fastapi import APIRouter, Depends, HTTPException
from backend.data.data_locker import DataLocker
from backend.deps import get_app_locker

router = APIRouter(prefix="/prices", tags=["prices"])

@router.get("/", response_model=list[dict])
def list_prices(dl: DataLocker = Depends(get_app_locker)):
    """Return all price entries ordered by most recent."""
    try:
        return dl.prices.get_all_prices()
    except Exception as exc:  # pragma: no cover - unexpected
        raise HTTPException(500, "Read failed") from exc
