from fastapi import APIRouter, Depends, HTTPException
from backend.models.trader import Trader
from data.dl_traders import DLTraderManager
from backend.data.data_locker import DataLocker

router = APIRouter(prefix="/api/traders", tags=["traders"])


def _dl() -> DataLocker:
    return DataLocker.get_instance()

@router.get("/", response_model=list[Trader])
async def get_traders(dl: DataLocker = Depends(_dl)):
    return dl.traders.list_traders()

@router.get("/{name}", response_model=Trader)
async def get_trader(name: str, dl: DataLocker = Depends(_dl)):
    trader = dl.traders.get_trader_by_name(name)
    if trader is None:
        raise HTTPException(status_code=404, detail="Trader not found")
    return trader

@router.post("/", status_code=201)
async def create_trader(trader: Trader, dl: DataLocker = Depends(_dl)):
    if dl.traders.create_trader(trader):
        return {"status": "created"}
    raise HTTPException(status_code=400, detail=dl.traders.last_error)

@router.put("/{name}")
async def update_trader(name: str, trader: dict, dl: DataLocker = Depends(_dl)):
    dl.traders.update_trader(name, trader)
    return {"status": "updated"}

@router.delete("/{name}")
async def delete_trader(name: str, dl: DataLocker = Depends(_dl)):
    if dl.traders.delete_trader(name):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Trader not found")
