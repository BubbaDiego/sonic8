"""
Raydium REST API client (read-only).
We only touch endpoints that are public in their SDK URL table.

Refs from their TS SDK URL config:
- BASE_HOST: https://api-v3.raydium.io
- POOL_SEARCH_BY_ID: /pools/info/ids
- MINT_PRICE: /mint/price
"""

import json
import time
from typing import Dict, List, Any, Optional
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError

from .constants import RAYDIUM_API_BASE


class RaydiumHttpError(RuntimeError):
    pass


class RaydiumApi:
    def __init__(self, base: str = RAYDIUM_API_BASE, timeout: float = 12.0):
        self.base = base.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base}{path}"
        if params:
            url = f"{url}?{urlencode(params, doseq=True)}"
        req = Request(url, headers={"User-Agent": "sonic/1.0"})
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            raise RaydiumHttpError(f"HTTP {e.code} for {url}: {e.read()}") from e
        except URLError as e:
            raise RaydiumHttpError(f"Network error for {url}: {e}") from e

    # ---- endpoints ----
    def pools_by_ids(self, ids: List[str]) -> Dict[str, Any]:
        if not ids:
            return {}
        joined = ",".join(ids)
        data = self._get("/pools/info/ids", {"ids": joined})
        # data: { data: [ {...}, ... ] } normally; normalize map by id
        out: Dict[str, Any] = {}
        items = (data.get("data") if isinstance(data, dict) else None) or []
        for it in items:
            pool_id = it.get("id") or it.get("pool_id") or it.get("poolId")
            if pool_id:
                out[pool_id] = it
        return out

    def mint_prices(self, mints: List[str]) -> Dict[str, float]:
        if not mints:
            return {}
        joined = ",".join(mints)
        data = self._get("/mint/price", {"mints": joined})
        # Expected format: { data: { "<mint>": <price>, ... } }
        mp = ((data or {}).get("data")) or {}
        # Normalize to float
        return {k: float(v) for k, v in mp.items() if v is not None}
