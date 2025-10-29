from __future__ import annotations

import sqlite3
import time
from typing import Any, Dict, List, Optional

import requests

from ..config import get_config


class TxService:
    """Helpers for inspecting and waiting on Solana transactions."""

    def __init__(self) -> None:
        self.cfg = get_config()
        self.rpc = self.cfg.solana_rpc_url

    # ---------- RPC helpers ----------
    def _rpc(self, method: str, params: List[Any]) -> Dict[str, Any]:
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        resp = requests.post(self.rpc, json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()

    # ---------- Status / confirm ----------
    def get_signature_status(self, signature: str) -> Dict[str, Any]:
        payload = [
            [signature],
            {"searchTransactionHistory": True},
        ]
        response = self._rpc("getSignatureStatuses", payload)
        value = (response.get("result") or {}).get("value") or []
        status = value[0] if value else None
        if not status:
            return {"found": False}
        return {
            "found": True,
            "slot": status.get("slot"),
            "confirmations": status.get("confirmations"),
            "confirmationStatus": status.get("confirmationStatus"),
            "err": status.get("err"),
        }

    def wait_for_confirmation(
        self,
        signature: str,
        desired: str = "confirmed",  # processed | confirmed | finalized
        timeout_s: int = 60,
        poll_ms: int = 750,
    ) -> Dict[str, Any]:
        deadline = time.time() + timeout_s
        order = {"processed": 0, "confirmed": 1, "finalized": 2}
        want = order.get(desired, 1)
        last: Optional[Dict[str, Any]] = None
        while time.time() < deadline:
            status = self.get_signature_status(signature)
            last = status
            if status.get("found"):
                confirmation_status = status.get("confirmationStatus") or "processed"
                level = order.get(confirmation_status, 0)
                if status.get("err") is None and level >= want:
                    status["ok"] = True
                    return status
                if status.get("err") is not None:
                    status["ok"] = False
                    return status
            time.sleep(poll_ms / 1000.0)
        last = last or {}
        last["ok"] = False
        last["timeout"] = True
        return last

    # ---------- Logs / transaction ----------
    def get_transaction_logs(self, signature: str) -> Dict[str, Any]:
        params = [signature, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
        response = self._rpc("getTransaction", params)
        result = response.get("result")
        if not result:
            return {"found": False}
        meta = result.get("meta") or {}
        return {
            "found": True,
            "slot": result.get("slot"),
            "err": meta.get("err"),
            "logMessages": meta.get("logMessages") or [],
        }

    # ---------- Helpers ----------
    def explorer_url(self, signature: str) -> str:
        return f"https://explorer.solana.com/tx/{signature}"

    def last_logged_signature(self) -> Optional[str]:
        try:
            db_path = self.cfg.mother_db_path
            with sqlite3.connect(db_path) as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "SELECT signature FROM jupiter_txlog "
                    "WHERE signature IS NOT NULL AND signature <> '' "
                    "ORDER BY id DESC LIMIT 1"
                )
                row = cursor.fetchone()
        except Exception:
            return None
        if not row:
            return None
        signature = row[0]
        return signature or None
