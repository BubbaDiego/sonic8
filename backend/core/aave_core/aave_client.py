from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

import requests

from .aave_config import AaveConfig

log = logging.getLogger(__name__)


class AaveGraphQLError(RuntimeError):
    pass


def _to_graphql_input(value: Any) -> str:
    """
    Serialize a Python dict/list/primitive into GraphQL input syntax.
    Strings are quoted, dict keys are emitted bare (GraphQL style).
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        # naive escaping for quotes/backslashes
        s = value.replace("\\", "\\\\").replace('"', '\"')
        return f'"{s}"'
    if isinstance(value, list):
        return "[" + ", ".join(_to_graphql_input(v) for v in value) + "]"
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            parts.append(f"{k}: {_to_graphql_input(v)}")
        return "{" + ", ".join(parts) + "}"
    # fallback to JSON string
    return _to_graphql_input(str(value))


class AaveGraphQLClient:
    """
    Minimal HTTP client for Aave V3 GraphQL.
    - Read queries (markets + user positions).
    - Transaction queries (supply/withdraw/borrow/repay) → ExecutionPlan.
    Docs: https://api.v3.aave.com/graphql (ExecutionPlan / TransactionRequest union). 
    """

    # ---------------- plumbing ----------------

    def __init__(self, cfg: AaveConfig):
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def execute(self, query: str) -> Dict[str, Any]:
        payload = {"query": query}
        t0 = time.time()
        r = self.session.post(self.cfg.graphql_url, data=json.dumps(payload), timeout=self.cfg.http_timeout_sec)
        dt = time.time() - t0
        try:
            data = r.json()
        except Exception as e:  # noqa: BLE001
            raise AaveGraphQLError(f"Bad JSON from Aave GraphQL: {r.status_code}, {r.text[:200]}") from e

        if "errors" in data and data["errors"]:
            log.error("Aave GraphQL errors: %s", data["errors"])
            raise AaveGraphQLError(str(data["errors"]))

        log.debug("Aave GraphQL ok (%.2fs)", dt)
        return data["data"]

    # ---------------- reads ----------------

    def fetch_market(self) -> Dict[str, Any]:
        # Conservative set of fields seen in Aave examples
        q = f"""
        query {{
          market(chainId: {self.cfg.chain_id}) {{
            reserves {{
              symbol
              underlyingAddress
              decimals
              ltv
              liquidationThreshold
              supplyApy
              variableBorrowApy
            }}
          }}
        }}
        """
        return self.execute(q)

    def fetch_user_positions(self, user: str) -> Dict[str, Any]:
        q = f"""
        query {{
          market(chainId: {self.cfg.chain_id}) {{
            user(address: "{user}") {{
              reserves {{
                reserve {{
                  symbol
                  underlyingAddress
                  decimals
                }}
                suppliedUsd
                borrowedUsd
                supplied
                borrowed
                usageAsCollateralEnabledOnUser
              }}
              accountData {{
                totalCollateralUsd
                totalDebtUsd
                healthFactor
              }}
            }}
          }}
        }}
        """
        return self.execute(q)

    # ---------------- transactions (ExecutionPlan) ----------------
    # We build inline-argument queries to avoid guessing input types.
    # Returned union members per docs: TransactionRequest | ApprovalRequired | InsufficientBalanceError.

    _TX_FIELDS = """
      __typename
      ... on TransactionRequest { to data value chainId operation }
      ... on ApprovalRequired { approval { to data value chainId operation } originalTransaction { to data value chainId operation } }
      ... on InsufficientBalanceError { required { value } }
    """

    def _markets_input(self, market_address: Optional[str]) -> str:
        """
        Aave docs commonly pass markets as [{ chainId, market }].
        If a Pool address isn't configured, we pass only chainId.
        """
        if market_address:
            req = [{"chainId": self.cfg.chain_id, "market": market_address}]
        else:
            req = [{"chainId": self.cfg.chain_id}]
        return _to_graphql_input(req)

    def plan_supply(self, *, market: Optional[str], user: str, reserve: str, amount: str) -> Dict[str, Any]:
        request = {
            "markets": json.loads(self._markets_input(market)),
            "user": user,
            "reserve": reserve,
            "amount": {"value": amount},
        }
        q = f"""
        query {{
          supply(request: {_to_graphql_input(request)}) {{
            {self._TX_FIELDS}
          }}
        }}
        """
        data = self.execute(q)
        return data["supply"]

    def plan_withdraw(self, *, market: Optional[str], user: str, reserve: str, amount: str) -> Dict[str, Any]:
        request = {
            "markets": json.loads(self._markets_input(market)),
            "user": user,
            "reserve": reserve,
            "amount": {"value": amount},
        }
        q = f"""
        query {{
          withdraw(request: {_to_graphql_input(request)}) {{
            {self._TX_FIELDS}
          }}
        }}
        """
        data = self.execute(q)
        return data["withdraw"]

    def plan_borrow(self, *, market: Optional[str], user: str, reserve: str, amount: str) -> Dict[str, Any]:
        request = {
            "markets": json.loads(self._markets_input(market)),
            "user": user,
            "reserve": reserve,
            "amount": {"value": amount},
        }
        q = f"""
        query {{
          borrow(request: {_to_graphql_input(request)}) {{
            {self._TX_FIELDS}
          }}
        }}
        """
        data = self.execute(q)
        return data["borrow"]

    def plan_repay(self, *, market: Optional[str], user: str, reserve: str, amount: str) -> Dict[str, Any]:
        request = {
            "markets": json.loads(self._markets_input(market)),
            "user": user,
            "reserve": reserve,
            "amount": {"value": amount},
        }
        q = f"""
        query {{
          repay(request: {_to_graphql_input(request)}) {{
            {self._TX_FIELDS}
          }}
        }}
        """
        data = self.execute(q)
        return data["repay"]
