from __future__ import annotations

from typing import Optional

from backend.core.raydium_core.xcom_core import RaydiumXCom
from backend.data.data_locker import DataLocker


def scan_owner_nfts(owner: str, dl: Optional[DataLocker] = None) -> int:
    """
    Discover an owner's CLMM position NFTs (using the TS helper's scan path),
    and persist slim rows to the DB via dl.raydium.

    Returns number of rows upserted.
    """

    # The TS helper enumerates dec=0 mints when no explicit mints are passed.
    xcom = RaydiumXCom()
    res = xcom.value_nfts(owner=owner, mints=None)
    payload = {}
    # Prefer richer details if available
    if res.get("details"):
        payload = {"details": res["details"]}
    else:
        payload = {"rows": res.get("rows", [])}

    dl = dl or DataLocker.get_instance()
    if getattr(dl, "raydium", None):
        return dl.raydium.upsert_from_ts_payload(owner, payload)
    return 0
