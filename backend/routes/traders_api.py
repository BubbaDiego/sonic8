
from fastapi import APIRouter, HTTPException
from backend.models.trader import Trader
from backend.dl_traders import DLTraderManager

router = APIRouter()

# Assume database object is initialized somewhere in your app
db = None
trader_manager = DLTraderManager(db)

@router.get("/traders", response_model=list[Trader])
async def get_traders():
    return trader_manager.list_traders()

@router.get("/traders/{name}", response_model=Trader)
async def get_trader(name: str):
    trader = trader_manager.get_trader_by_name(name)
    if trader is None:
        raise HTTPException(status_code=404, detail="Trader not found")
    return trader

@router.post("/traders", status_code=201)
async def create_trader(trader: Trader):
    if trader_manager.create_trader(trader):
        return {"status": "created"}
    raise HTTPException(status_code=400, detail=trader_manager.last_error)

@router.put("/traders/{name}")
async def update_trader(name: str, trader: dict):
    trader_manager.update_trader(name, trader)
    return {"status": "updated"}

@router.delete("/traders/{name}")
async def delete_trader(name: str):
    if trader_manager.delete_trader(name):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Trader not found")
