from fastapi import APIRouter, BackgroundTasks, Depends
from data.data_locker import DataLocker
from cyclone.services.position_service import CyclonePositionService

router = APIRouter(prefix="/cyclone/positions", tags=["cyclone-positions"])

def _service() -> CyclonePositionService:
    dl = DataLocker.get_instance()
    return CyclonePositionService(dl)

@router.post("/update", summary="Run Jupiter position sync in background", status_code=202)
async def update_positions(bg: BackgroundTasks):
    svc = _service()
    bg.add_task(svc.update_positions_from_jupiter)
    return {"msg": "Position sync started"}

@router.post("/enrich", summary="Enrich all positions with live data", status_code=202)
async def enrich(bg: BackgroundTasks):
    svc = _service()
    bg.add_task(lambda: svc.loop.run_until_complete(svc.enrich_positions()))
    return {"msg": "Enrichment started"}