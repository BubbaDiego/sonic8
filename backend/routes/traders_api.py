from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from backend.models.trader import Trader
from data.dl_traders import DLTraderManager, ACTIVE_TRADERS_JSON_PATH
from backend.data.data_locker import DataLocker
from backend.deps import get_locker
import os

router = APIRouter(prefix="/api/traders", tags=["traders"])

@router.get("/", response_model=list[Trader])
async def get_traders(dl: DataLocker = Depends(get_locker)):
    return dl.traders.list_traders()

@router.get("/{name}", response_model=Trader)
async def get_trader(name: str, dl: DataLocker = Depends(get_locker)):
    trader = dl.traders.get_trader_by_name(name)
    if trader is None:
        raise HTTPException(status_code=404, detail="Trader not found")
    return trader

@router.post("/", status_code=201)
async def create_trader(trader: Trader, dl: DataLocker = Depends(get_locker)):
    if dl.traders.create_trader(trader):
        return {"status": "created"}
    raise HTTPException(status_code=400, detail=dl.traders.last_error)

@router.put("/{name}")
async def update_trader(name: str, trader: dict, dl: DataLocker = Depends(get_locker)):
    dl.traders.update_trader(name, trader)
    return {"status": "updated"}

@router.delete("/{name}")
async def delete_trader(name: str, dl: DataLocker = Depends(get_locker)):
    if dl.traders.delete_trader(name):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Trader not found")

# NEW QUICK IMPORT ENDPOINT
@router.post("/quick_import", status_code=201)
async def quick_import_traders(dl: DataLocker = Depends(get_locker)):
    if dl.traders.quick_import_from_wallets():
        return {"status": "created"}
    raise HTTPException(status_code=400, detail="Quick import failed")


@router.get("/export")
async def export_traders(dl: DataLocker = Depends(get_locker)):
    """Export traders to ``active_traders.json`` and return the file."""
    path = str(ACTIVE_TRADERS_JSON_PATH)
    dl.traders.export_to_json(path)
    return FileResponse(path, filename=os.path.basename(path), media_type="application/json")
