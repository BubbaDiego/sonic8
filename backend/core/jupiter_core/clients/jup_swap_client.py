from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from ..config import JupiterConfig
from ..errors import JupiterHTTPError


class JupSwapClient:
    """Client for the legacy Jupiter Swap API."""

    def __init__(self, cfg: JupiterConfig, session: Optional[requests.Session] = None) -> None:
        self.cfg = cfg
        self.session = session or requests.Session()
        self.timeout = 20

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.cfg.api_key:
            headers["Authorization"] = f"Bearer {self.cfg.api_key}"
        return headers

    def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50,
        swap_mode: str = "ExactIn",
        only_direct_routes: bool = False,
        as_legacy_tx: bool = False,
    ) -> Dict[str, Any]:
        """Fetch a swap quote."""

        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": str(slippage_bps),
            "swapMode": swap_mode,
            "onlyDirectRoutes": "true" if only_direct_routes else "false",
            "asLegacyTransaction": "true" if as_legacy_tx else "false",
        }
        url = f"{self.cfg.swap_base}/swap/v1/quote"
        resp = self.session.get(url, params=params, headers=self._headers(), timeout=self.timeout)
        if resp.status_code >= 400:
            raise JupiterHTTPError(resp.status_code, "Quote failed", resp.text)
        return resp.json()

    def post_swap(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Build a swap transaction through the legacy API."""

        url = f"{self.cfg.swap_base}/swap/v1/swap"
        resp = self.session.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
        if resp.status_code >= 400:
            raise JupiterHTTPError(resp.status_code, "Swap build failed", resp.text)
        return resp.json()
