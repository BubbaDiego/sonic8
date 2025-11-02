from __future__ import annotations

import json
from typing import Any, Dict
from urllib.request import Request, urlopen


class RpcError(RuntimeError):
    pass


class SolanaRpcClient:
    def __init__(self, http_url: str, timeout: float = 20.0):
        self.url = http_url
        self.timeout = timeout

    def _call(self, method: str, params: list) -> Any:
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
        req = Request(self.url, data=body, headers={"Content-Type": "application/json", "User-Agent": "sonic7-core"})
        with urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if "error" in data:
            raise RpcError(f"{method} error: {data['error']}")
        return data["result"]

    def get_health(self) -> str:
        # Not all nodes implement getHealth; return "ok" if getSlot works.
        try:
            return self._call("getHealth", [])
        except Exception:
            self.get_slot()
            return "ok"

    def get_slot(self) -> int:
        return int(self._call("getSlot", []))
