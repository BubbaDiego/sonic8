from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..clients.gmx_rest_client import GmxRestClient
from ..clients.subsquid_client import SubsquidClient, POSITIONS_BY_ACCOUNT

@dataclass
class GMXPosition:
    account: str
    market_address: str
    is_long: bool
    size_usd: float
    size_in_tokens: float
    collateral_token: str
    collateral_amount: float
    entry_price: float
    liquidation_price: Optional[float]
    created_at: int
    updated_at: int

@dataclass
class NormalizedPosition:
    venue: str           # "GMX_V2"
    chain: str           # "arbitrum" | "avalanche"
    account: str
    symbol: str          # best-effort, e.g., "ETH-USD" (fallback to market_address)
    side: str            # "LONG" | "SHORT"
    size_usd: float
    entry_price: float
    mark_price: float
    collateral_token: str
    collateral_amount: float
    liquidation_price: Optional[float]
    market_address: str

class GMXPositionSource:
    """
    Read-only source:
      - Positions: Subsquid v2 (GraphQL)
      - Prices / markets: REST v2
    """
    def __init__(self, chain_key: str, rest: GmxRestClient, subsquid: SubsquidClient):
        self.chain_key = chain_key
        self.rest = rest
        self.squid = subsquid

    # ---- public API expected by positions_core sync service
    def list_open_positions(self, wallet: str, limit: int = 1000) -> List[GMXPosition]:
        data = self.squid.query(POSITIONS_BY_ACCOUNT, {"account": wallet.lower(), "limit": limit})
        rows = (data.get("data") or {}).get("positions") or []
        out: List[GMXPosition] = []
        for r in rows:
            out.append(
                GMXPosition(
                    account=r.get("account"),
                    market_address=r.get("marketAddress"),
                    is_long=bool(r.get("isLong")),
                    size_usd=float(r.get("sizeUsd") or 0),
                    size_in_tokens=float(r.get("sizeInTokens") or 0),
                    collateral_token=(r.get("collateralToken") or "").lower(),
                    collateral_amount=float(r.get("collateralAmount") or 0),
                    entry_price=float(r.get("entryPrice") or 0),
                    liquidation_price=float(r["liquidationPrice"]) if r.get("liquidationPrice") is not None else None,
                    created_at=int(r.get("createdAt") or 0),
                    updated_at=int(r.get("updatedAt") or 0),
                )
            )
        return out

    def normalize(self, positions: List[GMXPosition]) -> List[NormalizedPosition]:
        # Fetch mark prices
        tickers = self.rest.get_tickers()  # tokenSymbol -> { price: ... }
        token_prices: Dict[str, float] = {}
        # GMX tickers payload is { "ETH": {..., "price": 3400.1}, ... }
        for sym, obj in (tickers or {}).items():
            try:
                token_prices[sym.upper()] = float(obj.get("price"))
            except Exception:
                continue

        # Attempt to derive a human symbol using markets/info (optional)
        markets_info = self.rest.get_markets_info()
        addr_to_symbol: Dict[str, str] = {}
        # We accept various shapes; best effort mapping
        # e.g., markets_info = { "markets": [ { "address": "0x...", "indexToken": {"symbol":"ETH"} }, ... ] }
        if isinstance(markets_info, dict):
            for k in ("markets", "marketsInfo", "data"):
                seq = markets_info.get(k)
                if isinstance(seq, list):
                    for m in seq:
                        addr = (m.get("address") or m.get("market") or "").lower()
                        idx_sym = None
                        if isinstance(m.get("indexToken"), dict):
                            idx_sym = m["indexToken"].get("symbol")
                        elif "indexTokenSymbol" in m:
                            idx_sym = m.get("indexTokenSymbol")
                        if addr and idx_sym:
                            addr_to_symbol[addr] = f"{idx_sym.upper()}-USD"

        result: List[NormalizedPosition] = []
        for p in positions:
            sym_guess = addr_to_symbol.get(p.market_address.lower(), p.market_address)
            # try to select a mark price (index token)
            mark = 0.0
            if isinstance(sym_guess, str) and sym_guess.endswith("-USD"):
                idx = sym_guess.split("-")[0]
                mark = token_prices.get(idx, p.entry_price or 0.0)
            else:
                mark = p.entry_price or 0.0

            result.append(
                NormalizedPosition(
                    venue="GMX_V2",
                    chain=self.chain_key,
                    account=p.account,
                    symbol=sym_guess,
                    side="LONG" if p.is_long else "SHORT",
                    size_usd=p.size_usd,
                    entry_price=p.entry_price,
                    mark_price=mark,
                    collateral_token=p.collateral_token,
                    collateral_amount=p.collateral_amount,
                    liquidation_price=p.liquidation_price,
                    market_address=p.market_address,
                )
            )
        return result
