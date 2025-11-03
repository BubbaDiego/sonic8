from __future__ import annotations

import os
import time
from typing import Any, Dict, Iterable, List, Optional

import requests
from requests import Session

from solana.publickey import PublicKey
from solana.rpc.api import Client as SolanaClient

from backend.core.raydium_core.raydium_constants import (
    DEFAULT_RAYDIUM_API_BASE,
    RAYDIUM_API_PATHS,
    DEFAULT_TIMEOUT_SEC,
    DEFAULT_RETRY,
    TOKEN_PROGRAM_ID,
    TOKEN_2022_PROGRAM_ID,
)


def _retry(fn, attempts=DEFAULT_RETRY, delay=0.5, backoff=2.0):
    last = None
    for i in range(1, attempts + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            if i >= attempts:
                break
            time.sleep(delay)
            delay *= backoff
    raise last


class RaydiumAPI:
    """
    Thin HTTP client around Raydium public V3 API.

    Base and endpoints follow the official SDK's `API_URLS` mapping so we stay compatible.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        session: Optional[Session] = None,
        timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    ):
        self.base = base_url or os.getenv("RAYDIUM_API_BASE", DEFAULT_RAYDIUM_API_BASE)
        self.s = session or requests.Session()
        self.timeout = timeout_sec

    def _abs(self, path_key: str) -> str:
        path = RAYDIUM_API_PATHS[path_key]
        if path.startswith("http"):
            return path
        return f"{self.base.rstrip('/')}{path}"

    # --- token endpoints ---
    def get_token_list(self) -> List[Dict[str, Any]]:
        url = self._abs("TOKEN_LIST")
        return _retry(lambda: self.s.get(url, timeout=self.timeout).json())

    # --- pool endpoints ---
    def get_pool_list(self, **params) -> Dict[str, Any]:
        url = self._abs("POOL_LIST")
        query = {k: v for k, v in (params or {}).items() if v is not None}
        return _retry(lambda: self.s.get(url, params=query or None, timeout=self.timeout).json())

    def fetch_pool_by_id(self, ids: Iterable[str]) -> Dict[str, Any]:
        url = self._abs("POOL_SEARCH_BY_ID")
        q = {"ids": ",".join(ids)}
        return _retry(lambda: self.s.get(url, params=q, timeout=self.timeout).json())

    def fetch_pool_by_mints(self, mint1: str, mint2: Optional[str] = None, **params) -> Dict[str, Any]:
        url = self._abs("POOL_SEARCH_MINT")
        q = {"mint1": mint1}
        if mint2:
            q["mint2"] = mint2
        q.update({k: v for k, v in (params or {}).items() if v is not None})
        return _retry(lambda: self.s.get(url, params=q or None, timeout=self.timeout).json())


class RaydiumDataLayer:
    """
    IO boundary for Raydium + Solana:
      - Solana RPC (balances)
      - Raydium public API (token list, pools)
    """

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        raydium_api_base: Optional[str] = None,
        session: Optional[Session] = None,
    ):
        self.rpc_url = rpc_url or os.getenv("RPC_URL") or "https://api.mainnet-beta.solana.com"
        self.sol = SolanaClient(self.rpc_url)
        self.api = RaydiumAPI(base_url=raydium_api_base, session=session)

    # --------- wallet balances (headless) ---------
    def _get_sol_balance(self, owner: str) -> Dict[str, Any]:
        resp = _retry(lambda: self.sol.get_balance(PublicKey(owner)))
        lamports = int(resp["result"]["value"])
        # include context slot for traceability
        ctx_slot = resp.get("result", {}).get("context", {}).get("slot") or resp.get("context", {}).get("slot")
        return {"lamports": lamports, "slot": ctx_slot}

    def _get_token_accounts_by_owner(self, owner: str, program_id: str) -> Dict[str, Any]:
        return _retry(
            lambda: self.sol.get_token_accounts_by_owner_json_parsed(
                PublicKey(owner), {"programId": str(program_id)}
            )
        )

    def get_wallet_balances(self, owner: str, include_zero: bool = False) -> Dict[str, Any]:
        sol_bal = self._get_sol_balance(owner)
        # fetch both SPL versions
        classic = self._get_token_accounts_by_owner(owner, TOKEN_PROGRAM_ID)["result"]
        token22 = self._get_token_accounts_by_owner(owner, TOKEN_2022_PROGRAM_ID)["result"]

        all_vals: List[Dict[str, Any]] = []
        for bucket, program in [(classic, TOKEN_PROGRAM_ID), (token22, TOKEN_2022_PROGRAM_ID)]:
            for v in bucket.get("value", []):
                acc = v.get("account", {})
                parsed = (acc.get("data") or {}).get("parsed") or {}
                info = parsed.get("info") or {}
                amount = info.get("tokenAmount") or {}
                ui = amount.get("uiAmount")
                decimals = int(amount.get("decimals") or 0)
                raw = int(amount.get("amount") or 0)
                if not include_zero and raw == 0:
                    continue
                all_vals.append(
                    {
                        "mint": info.get("mint"),
                        "amount_raw": raw,
                        "decimals": decimals,
                        "ui_amount": float(ui or (raw / (10**decimals if decimals else 1))),
                        "ata": v.get("pubkey"),
                        "symbol": None,  # filled optionally by enrich step
                        "token_program": "token-2022" if program == TOKEN_2022_PROGRAM_ID else "token",
                    }
                )

        return {
            "owner": owner,
            "sol_lamports": sol_bal["lamports"],
            "sol": sol_bal["lamports"] / 1e9,
            "tokens": all_vals,
            "context_slot": sol_bal["slot"],
        }

    # --------- enrichment (optional) ---------
    def enrich_token_metadata(self, balances: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attach symbol/decimals/name from Raydium token list if available.
        """
        try:
            tokens = self.api.get_token_list()  # list of {address, symbol, name, decimals, ...}
            by_mint = {t.get("address"): t for t in tokens if t.get("address")}
        except Exception:
            return balances  # silent best-effort
        for t in balances.get("tokens", []):
            meta = by_mint.get(t["mint"])
            if meta:
                t["symbol"] = meta.get("symbol") or t.get("symbol")
                # prefer on-chain decimals where present; else fill
                if not t.get("decimals") and meta.get("decimals") is not None:
                    t["decimals"] = int(meta["decimals"])
        return balances

    # --------- pass-through Raydium Public API ---------
    def get_token_list(self) -> List[Dict[str, Any]]:
        return self.api.get_token_list()

    def get_pool_list(self, **params) -> Dict[str, Any]:
        return self.api.get_pool_list(**params)

    def fetch_pool_by_id(self, ids: Iterable[str]) -> Dict[str, Any]:
        return self.api.fetch_pool_by_id(ids)

    def fetch_pool_by_mints(self, mint1: str, mint2: Optional[str] = None, **params) -> Dict[str, Any]:
        return self.api.fetch_pool_by_mints(mint1, mint2, **params)
