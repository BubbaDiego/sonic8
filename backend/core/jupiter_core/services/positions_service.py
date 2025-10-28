from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests


class PositionsService:
    """Best-effort probe for open Jupiter Perps positions via Sonic API."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base = base_url or os.getenv("SONIC_API_BASE")

    def probe_positions(self, owner_pubkey: str) -> Dict[str, Any]:
        """Query several known endpoints until one responds with positions."""

        if not self.base:
            return {"error": "SONIC_API_BASE not set; cannot query positions API."}

        candidates: List[str] = [
            "/api/jupiter/perps/positions",
            "/api/perps/positions",
            "/api/positions",
        ]
        session = requests.Session()
        for path in candidates:
            url = self.base.rstrip("/") + path
            try:
                response = session.get(url, params={"owner": owner_pubkey}, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    positions = data.get("positions")
                    if positions is None and isinstance(data, list):
                        positions = data
                    elif positions is None:
                        positions = []
                    return {"endpoint": url, "positions": positions}
            except Exception:  # pragma: no cover - depends on external service
                continue
        return {"error": f"No positions endpoint responded under {self.base}"}
