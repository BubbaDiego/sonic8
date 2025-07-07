from fastapi import APIRouter, Depends, HTTPException
from backend.data.data_locker import DataLocker
from backend.models.portfolio import PortfolioSnapshot

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _dl() -> DataLocker:
    return DataLocker.get_instance()


@router.get("/", response_model=list[PortfolioSnapshot])
def list_portfolio_history(dl: DataLocker = Depends(_dl)):
    return dl.get_portfolio_history()


@router.get("/latest", response_model=PortfolioSnapshot | None)
def get_latest_snapshot(dl: DataLocker = Depends(_dl)):
    return dl.portfolio.get_latest_snapshot()


@router.post("/", status_code=201)
def add_portfolio_entry(entry: PortfolioSnapshot, dl: DataLocker = Depends(_dl)):
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
def update_portfolio_entry(entry_id: str, fields: dict, dl: DataLocker = Depends(_dl)):
    dl.update_portfolio_entry(entry_id, fields)
    return {"status": "updated"}


@router.delete("/{entry_id}")
def delete_portfolio_entry(entry_id: str, dl: DataLocker = Depends(_dl)):
    dl.delete_portfolio_entry(entry_id)
    return {"status": "deleted"}
