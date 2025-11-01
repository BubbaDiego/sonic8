import json
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

Json = Dict[str, Any]

class GqlError(RuntimeError):
    pass

class SubsquidClient:
    """
    Thin GraphQL client for GMX Synthetics Squid (v2).
    Use :prod endpoints per GMX announcements.
    """
    def __init__(self, url: str, timeout: float = 12.0, ua: str = "sonic7-gmx-core/phase2"):
        self.url = url
        self.timeout = timeout
        self.ua = ua

    def query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Json:
        body = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
        req = Request(
            self.url,
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": self.ua},
        )
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as e:
            raise GqlError(f"Subsquid error: {e}") from e

        if "errors" in data:
            raise GqlError(f"Subsquid returned errors: {data['errors']}")
        return data

# ---- Sample queries (schema may evolve; adjust in Phase 2.1 if fields differ)
# GMX announced entity/field renames and :prod migration on 2025-04-29. :contentReference[oaicite:5]{index=5}
POSITIONS_BY_ACCOUNT = """
query PositionsByAccount($account: String!, $limit: Int!) {
  positions(
    where: { account_eq: $account, isOpen_eq: true }
    limit: $limit
    orderBy: updatedAt_DESC
  ) {
    id
    account
    marketAddress
    collateralToken
    isLong
    sizeUsd
    sizeInTokens
    collateralAmount
    entryPrice
    liquidationPrice
    createdAt
    updatedAt
  }
}
"""
