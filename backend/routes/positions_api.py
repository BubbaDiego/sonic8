# backend/routes/positions_api.py
from fastapi import APIRouter, Depends, HTTPException
from models.position import Position
from data.data_locker import DataLocker
from core.positions_core.position_core import PositionCore

router = APIRouter(prefix="/positions", tags=["positions"])

def _dl():
    return DataLocker.get_instance()  # uses mother DB path

@router.get("/", response_model=list[dict])
def list_positions(dl: DataLocker = Depends(_dl)):
    return PositionCore(dl).get_all_positions()

@router.post("/", status_code=201)
def create_position(pos: Position, dl: DataLocker = Depends(_dl)):
    ok = PositionCore(dl).create_position(pos.dict())
    if not ok:
        raise HTTPException(500, "Insert failed")
    return {"status": "created"}

@router.delete("/{pos_id}")
def delete_position(pos_id: str, dl: DataLocker = Depends(_dl)):
    PositionCore(dl).delete_position(pos_id)
    return {"status": "deleted"}

@router.post("/snapshot")
def snapshot(dl: DataLocker = Depends(_dl)):
    PositionCore(dl).record_snapshot()
    return {"status": "snapshot recorded"}
