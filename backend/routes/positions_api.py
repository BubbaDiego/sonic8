# backend/routes/positions_api.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from backend.models.position import Position, PositionDB
from backend.data.data_locker import DataLocker
from backend.core.positions_core.position_core import PositionCore
from backend.services.position_service import CyclonePositionService
from backend.deps import get_app_locker

router = APIRouter(prefix="/positions", tags=["positions"])

@router.get("/", response_model=list[PositionDB])
def list_positions(dl: DataLocker = Depends(get_app_locker)):
    return PositionCore(dl).get_all_positions()

@router.post("/", status_code=201)
def create_position(pos: PositionDB, dl: DataLocker = Depends(get_app_locker)):
    ok = PositionCore(dl).create_position(pos)
    if not ok:
        raise HTTPException(500, "Insert failed")
    return {"status": "created"}

@router.delete("/{pos_id}")
def delete_position(pos_id: str, dl: DataLocker = Depends(get_app_locker)):
    PositionCore(dl).delete_position(pos_id)
    return {"status": "deleted"}

@router.post("/snapshot")
def snapshot(dl: DataLocker = Depends(get_app_locker)):
    PositionCore(dl).record_snapshot()
    return {"status": "snapshot recorded"}


@router.post("/update", status_code=202, summary="Run Jupiter position sync in background")
async def update_positions(bg: BackgroundTasks, dl: DataLocker = Depends(get_app_locker)):
    service = CyclonePositionService(dl)  # service instance
    bg.add_task(service.update_positions_from_jupiter)
    return {"msg": "Position sync started"}


@router.post("/enrich", status_code=202, summary="Enrich all positions with live data")
async def enrich(bg: BackgroundTasks, dl: DataLocker = Depends(get_app_locker)):
    service = CyclonePositionService(dl)
    bg.add_task(lambda: service.loop.run_until_complete(service.enrich_positions()))
    return {"msg": "Enrichment started"}
