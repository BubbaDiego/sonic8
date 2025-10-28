from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from ..config import JupiterConfig
from ..errors import JupiterHTTPError


class JupUltraClient:
    """Client for Jupiter Ultra order and execution APIs."""

    def __init__(self, cfg: JupiterConfig, session: Optional[requests.Session] = None) -> None:
        self.cfg = cfg
        self.session = session or requests.Session()
        self.timeout = 25

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.cfg.api_key:
            headers["Authorization"] = f"Bearer {self.cfg.api_key}"
        return headers

    def order(
        self,
        *,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50,
        user_public_key: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build an Ultra order returning a transaction to sign."""

        body: Dict[str, Any] = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount,
            "slippageBps": slippage_bps,
        }
        if user_public_key:
            body["userPublicKey"] = user_public_key
            body.setdefault("payer", user_public_key)
        if extra:
            body.update(extra)

        url = f"{self.cfg.ultra_base}/v1/order"
        resp = self.session.post(url, json=body, headers=self._headers(), timeout=self.timeout)
        if resp.status_code >= 400:
            raise JupiterHTTPError(resp.status_code, "Ultra order failed", resp.text)
        return resp.json()

    def execute(self, *, signed_tx_base64: str) -> Dict[str, Any]:
        """Submit a signed transaction through Ultra."""

        url = f"{self.cfg.ultra_base}/v1/execute"
        body = {"transaction": signed_tx_base64}
        resp = self.session.post(url, json=body, headers=self._headers(), timeout=self.timeout)
        if resp.status_code >= 400:
            raise JupiterHTTPError(resp.status_code, "Ultra execute failed", resp.text)
        return resp.json()
