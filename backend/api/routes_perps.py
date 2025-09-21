from fastapi import APIRouter, HTTPException, Body
from typing import Any, Dict
from ..services.perps_bridge.perps_service import dry_run_increase, PerpsCLIError

router = APIRouter(prefix="/api/perps", tags=["perps"])


@router.post("/dry-run/increase")
def api_perps_dry_run_increase(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Thin pass-through to the TS CLI (JSON in/JSON out).
    NOTE: Do not place secrets in the payload; pass only the minimal RPC endpoint/addresses.
    """
    try:
        return dry_run_increase(payload)
    except PerpsCLIError as e:
        raise HTTPException(status_code=422, detail={"message": str(e), "cli": e.payload})
