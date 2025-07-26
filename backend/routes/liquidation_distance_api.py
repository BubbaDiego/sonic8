from fastapi import APIRouter, Depends
from backend.data.data_locker import DataLocker
from backend.deps import get_app_locker

router = APIRouter(prefix="/api/liquidation", tags=["liquidation"])

@router.get("/nearest-distance")
def nearest_liq(dl: DataLocker = Depends(get_app_locker)):
    cursor = dl.db.get_cursor()
    if not cursor:
        return {}
    cursor.execute(
        """
        SELECT asset_type, MIN(ABS(liquidation_distance)) AS min_dist
          FROM positions
         WHERE status = 'ACTIVE'
      GROUP BY asset_type
        """
    )
    rows = cursor.fetchall() or []
    return {row["asset_type"]: round(row["min_dist"], 2) for row in rows}
