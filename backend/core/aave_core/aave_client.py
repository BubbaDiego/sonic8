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


class AaveGraphQLClient:
    """
    Thin HTTP client for Aave V3 GraphQL. We keep it generic and pass
    query strings so we can track doc-aligned shapes without inventing.
    """

    def __init__(self, cfg: AaveConfig):
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def execute(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {"query": query, "variables": variables or {}}
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

    # ——— Canonical queries (placeholders follow public docs naming) ———
    # These strings are kept here so Codex can swap to the exact sanctioned fragments if needed.

    Q_MARKET_RESERVES = """
    query MarketReserves($chainId: Int!) {
      market(chainId: $chainId) {
        reserves {
          symbol
          underlyingAddress
          decimals
          ltv
          liquidationThreshold
          supplyApy
          variableBorrowApy
        }
      }
    }
    """

    Q_USER_POSITIONS = """
    query UserPositions($chainId: Int!, $user: String!) {
      market(chainId: $chainId) {
        user(address: $user) {
          reserves {
            reserve {
              symbol
              underlyingAddress
              decimals
            }
            suppliedUsd
            borrowedUsd
            supplied
            borrowed
            usageAsCollateralEnabledOnUser
          }
          accountData {
            totalCollateralUsd
            totalDebtUsd
            healthFactor
          }
        }
      }
    }
    """

    def fetch_market(self) -> Dict[str, Any]:
        return self.execute(self.Q_MARKET_RESERVES, {"chainId": self.cfg.chain_id})

    def fetch_user_positions(self, user: str) -> Dict[str, Any]:
        return self.execute(self.Q_USER_POSITIONS, {"chainId": self.cfg.chain_id, "user": user})


Note: The field names in the queries above match current public examples. If the GraphQL schema differs, swap these with the sanctioned fragments; all upstream call sites are insulated behind this client.
