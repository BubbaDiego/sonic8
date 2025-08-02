from fastapi import APIRouter, Depends
from backend.data.data_locker import DataLocker
from backend.deps import get_app_locker

router = APIRouter(prefix="/api/liquidation", tags=["liquidation"])

@router.get("/nearest-distance")
def nearest_liq(dl: DataLocker = Depends(get_app_locker)):
    result = {"BTC": None, "ETH": None, "SOL": None}

    cursor = dl.db.get_cursor()
    if not cursor:
        return result

    cursor.execute(
        """
        WITH ranked AS (
            SELECT
                asset_type,
                position_type,
                ABS(liquidation_distance) AS dist,
                ROW_NUMBER() OVER (
                    PARTITION BY asset_type ORDER BY ABS(liquidation_distance)
                ) AS rnk
            FROM positions
            WHERE status = 'ACTIVE'
              AND liquidation_distance IS NOT NULL
        )
        SELECT asset_type, position_type, dist
          FROM ranked
         WHERE rnk = 1
        """
    )
    rows = cursor.fetchall() or []
    for row in rows:
        result[row["asset_type"]] = {
            "dist": round(row["dist"], 2),
            "side": row["position_type"],
        }

    return result
