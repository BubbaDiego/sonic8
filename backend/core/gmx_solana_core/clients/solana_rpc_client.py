"""
Thin Solana JSON-RPC client (stdlib only) for Phase S-2.1.

We avoid extra deps to keep 'markets' and 'positions' runnable with zero install.
"""
import json
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

Json = Dict[str, Any]

class RpcError(RuntimeError): ...

class SolanaRpcClient:
    def __init__(self, rpc_http: str, timeout: float = 12.0, ua: str = "sonic7-gmx-sol/phase2.1"):
        if not rpc_http:
            raise ValueError("rpc_http is required")
        self.url = rpc_http
        self.timeout = timeout
        self.ua = ua
        self._cid = 0

    def _call(self, method: str, params: Optional[List[Any]] = None) -> Json:
        self._cid += 1
        body = json.dumps({"jsonrpc": "2.0", "id": self._cid, "method": method, "params": params or []}).encode("utf-8")
        req = Request(self.url, data=body, headers={"Content-Type": "application/json", "User-Agent": self.ua})
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as e:
            raise RpcError(f"RPC {method} failed: {e}")
        if "error" in data:
            raise RpcError(f"RPC {method} returned error: {data['error']}")
        return data["result"]

    def get_program_accounts(self, program_id: str, encoding: str = "base64",
                             data_slice: Optional[Dict[str,int]] = None,
                             memcmp: Optional[List[Dict[str, str]]] = None,
                             commitment: str = "confirmed") -> List[Json]:
        cfg: Dict[str, Any] = {"encoding": encoding, "commitment": commitment}
        if data_slice:
            cfg["dataSlice"] = data_slice
        if memcmp:
            cfg["filters"] = [{"memcmp": m} for m in memcmp]
        return self._call("getProgramAccounts", [program_id, cfg])
