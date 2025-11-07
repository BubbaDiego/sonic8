from __future__ import annotations

from typing import List, Optional

from backend.core.raydium_core.xcom_core import RaydiumXCom
from backend.data.data_locker import DataLocker


def value_owner_nfts(owner: str, mints: Optional[List[str]] = None, price_url: Optional[str] = None) -> int:
    """
    Value CLMM NFTs for an owner (amounts A/B, prices, USD) and persist to DB.
    Returns number of rows upserted.
    """

    xcom = RaydiumXCom()
    res = xcom.value_nfts(owner=owner, mints=mints, price_url=price_url)
    payload = {}
    if res.get("details"):
        payload = {"details": res["details"]}
    else:
        payload = {"rows": res.get("rows", [])}

    dl = DataLocker.get_instance()
    if getattr(dl, "raydium", None):
        return dl.raydium.upsert_from_ts_payload(owner, payload)
    return 0
