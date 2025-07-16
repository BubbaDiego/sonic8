from fastapi import APIRouter, Depends, HTTPException
from backend.data.data_locker import DataLocker
from backend.models.portfolio import PortfolioSnapshot
from backend.deps import get_app_locker


def _dl() -> DataLocker:
    """Return the global :class:`DataLocker` instance."""
    return DataLocker.get_instance()

router = APIRouter(prefix="/portfolio", tags=["portfolio"])
api_router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/", response_model=list[PortfolioSnapshot])
def list_portfolio_history(dl: DataLocker = Depends(get_app_locker)):
    return dl.get_portfolio_history()


@router.get("/latest", response_model=PortfolioSnapshot | None)
def get_latest_snapshot(dl: DataLocker = Depends(get_app_locker)):
    return dl.portfolio.get_latest_snapshot()


@api_router.get("/latest_snapshot", response_model=PortfolioSnapshot | None)
def get_latest_snapshot_api(dl: DataLocker = Depends(_dl)):
    """Alias of /portfolio/latest that includes the /api prefix for
    backwards compatibility."""
    return dl.portfolio.get_latest_snapshot()


@router.post("/", status_code=201)
def add_portfolio_entry(entry: PortfolioSnapshot, dl: DataLocker = Depends(get_app_locker)):
    """Insert a portfolio history entry using the PortfolioSnapshot model."""
    try:
        if hasattr(entry, "model_dump"):
            data = entry.model_dump()
        else:
            data = entry.dict()
        dl.add_portfolio_entry(data)
    except Exception as exc:  # pragma: no cover - safety
        raise HTTPException(500, "Insert failed") from exc
    return {"status": "created"}


@router.put("/{entry_id}")
def update_portfolio_entry(entry_id: str, fields: dict, dl: DataLocker = Depends(get_app_locker)):
    dl.update_portfolio_entry(entry_id, fields)
    return {"status": "updated"}


@router.delete("/{entry_id}")
def delete_portfolio_entry(entry_id: str, dl: DataLocker = Depends(get_app_locker)):
    dl.delete_portfolio_entry(entry_id)
    return {"status": "deleted"}

@api_router.post("/update_snapshot", response_model=PortfolioSnapshot)
async def update_snapshot(
    snapshot: PortfolioSnapshot, dl: DataLocker = Depends(_dl)
):
    try:
        if hasattr(snapshot, "model_dump"):
            snap_data = snapshot.model_dump()
        elif hasattr(snapshot, "dict"):
            snap_data = snapshot.dict()
        else:
            snap_data = snapshot.__dict__

        session = None
        try:
            session = dl.session.get_active_session()
            if session:
                snap_data.setdefault("session_start_value", session.session_start_value or 0.0)
                snap_data.setdefault("session_goal_value", session.session_goal_value or 0.0)
        except Exception:  # pragma: no cover - defensive
            session = None

        snap_obj = PortfolioSnapshot(**snap_data)
        dl.portfolio.record_snapshot(snap_obj)

        if session:
            total_val = float(snap_data.get("total_value", 0.0) or 0.0)
            start_val = float(session.session_start_value or 0.0)
            delta = total_val - start_val

            try:
                dl.session.update_session(
                    session.id,
                    {
                        "current_session_value": delta,
                        "session_performance_value": delta,
                    },
                )
            except Exception:  # pragma: no cover - defensive
                pass

        return snap_obj
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
