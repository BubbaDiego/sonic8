
"""FastAPI router exposing /api/fun/random endpoint."""
from fastapi import APIRouter, Query, HTTPException
import logging

from .models import FunContent, FunType
from .registry import FunRegistry

router = APIRouter(prefix="/api/fun", tags=["fun"])

@router.get("/random", response_model=FunContent)
async def get_random_fun(type: FunType = Query(FunType.joke)):
    try:
        service = FunRegistry.by_type(type)
        return await service.get_random()
    except Exception as exc:  # noqa: BLE001
        logging.exception("fun_core failure")
        raise HTTPException(status_code=500, detail=str(exc))
