"""
Very small Solana JSON-RPC client (sync, no web3 dependency).
We only use a few methods: getParsedTokenAccountsByOwner, getProgramAccounts, getAccountInfo.
"""

import json
import os
import time
from base64 import b64decode
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from .constants import DEFAULT_TIMEOUT, TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID

Json = Dict[str, Any]


class JsonRpcError(RuntimeError):
    pass


class SolanaRPC:
    def __init__(self, rpc_url: Optional[str] = None, timeout: float = DEFAULT_TIMEOUT):
        self.rpc_url = rpc_url or os.getenv("RPC_URL") or "https://api.mainnet-beta.solana.com"
        self.timeout = timeout

    # ---- low-level ----
    def _send(self, method: str, params: List[Any]) -> Any:
        payload = {"jsonrpc": "2.0", "id": int(time.time() * 1_000), "method": method, "params": params}
        body = json.dumps(payload).encode("utf-8")
        req = Request(self.rpc_url, data=body, headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            raise JsonRpcError(f"HTTP {e.code} for {method}: {e.read()}") from e
        except URLError as e:
            raise JsonRpcError(f"RPC URL error for {method}: {e}") from e

        if "error" in data:
            raise JsonRpcError(f"RPC error for {method}: {data['error']}")
        return data["result"]

    # ---- helpers we need ----
    def get_parsed_token_accounts_by_owner(self, owner: str, program_id: str) -> List[Json]:
        params = [
            owner,
            {"programId": program_id},
            {"commitment": "confirmed"},
        ]
        res = self._send("getParsedTokenAccountsByOwner", params)
        return res.get("value", [])

    def get_program_accounts(self, program_id: str, filters: Optional[List[Json]] = None, encoding: str = "base64") -> List[Json]:
        cfg: Json = {"encoding": encoding}
        if filters:
            cfg["filters"] = filters
        params = [program_id, cfg]
        return self._send("getProgramAccounts", params)

    def get_account_info_base64(self, pubkey: str) -> Tuple[bytes, int]:
        res = self._send("getAccountInfo", [pubkey, {"encoding": "base64"}])
        value = res.get("value")
        if not value:
            return b"", 0
        data_b64, _encoding = value["data"]
        lamports = value.get("lamports", 0)
        return b64decode(data_b64), lamports
