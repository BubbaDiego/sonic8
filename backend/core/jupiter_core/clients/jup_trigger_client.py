from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from ..config import JupiterConfig
from ..errors import JupiterHTTPError


class JupTriggerClient:
    """Client for the Jupiter Trigger API."""

    def __init__(self, cfg: JupiterConfig, session: Optional[requests.Session] = None) -> None:
        self.cfg = cfg
        self.session = session or requests.Session()
        self.timeout = 20

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.cfg.api_key:
            headers["Authorization"] = f"Bearer {self.cfg.api_key}"
        return headers

    def list_orders(self, *, owner: str) -> Dict[str, Any]:
        url = f"{self.cfg.trigger_base}/v1/getTriggerOrders"
        resp = self.session.get(url, params={"owner": owner}, headers=self._headers(), timeout=self.timeout)
        if resp.status_code >= 400:
            raise JupiterHTTPError(resp.status_code, "List trigger orders failed", resp.text)
        return resp.json()

    def create_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.cfg.trigger_base}/v1/createOrder"
        resp = self.session.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
        if resp.status_code >= 400:
            raise JupiterHTTPError(resp.status_code, "Create trigger order failed", resp.text)
        return resp.json()

    def cancel_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.cfg.trigger_base}/v1/cancelOrder"
        resp = self.session.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
        if resp.status_code >= 400:
            raise JupiterHTTPError(resp.status_code, "Cancel trigger order failed", resp.text)
        return resp.json()
