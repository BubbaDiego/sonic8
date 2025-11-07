from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class NFT:
    """Generic NFT concept (protocol-agnostic)."""

    mint: str
    owner: Optional[str] = None
    standard: Optional[str] = None  # "SPL" | "Token-2022" | None
    name: Optional[str] = None
    collection: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClmmNFT(NFT):
    """
    Raydium CLMM position NFT (first-class DB concept).
    Mirrors the shape we persist and render across the stack.
    """

    pool_id: Optional[str] = None
    token_a_mint: Optional[str] = None
    token_b_mint: Optional[str] = None
    amount_a: Optional[float] = None
    amount_b: Optional[float] = None
    price_a: Optional[float] = None
    price_b: Optional[float] = None
    usd_total: Optional[float] = None
    in_range: Optional[bool] = None
    tick_lower: Optional[int] = None
    tick_upper: Optional[int] = None
    checked_at: Optional[str] = None  # ISO8601
    source: str = "raydium.sdk+jupiter"
    details: Dict[str, Any] = field(default_factory=dict)

    def ensure_checked(self) -> None:
        if not self.checked_at:
            self.checked_at = datetime.now(timezone.utc).isoformat()

    @staticmethod
    def from_panel_row(owner: str, row: Dict[str, Any]) -> "ClmmNFT":
        """
        Accepts the lightweight 'panelRows' produced by the TS helper:
          { name, address, chain, usd, checked }
        """

        mint = str(row.get("address") or "")
        n = ClmmNFT(
            mint=mint,
            owner=owner,
            usd_total=float(row.get("usd")) if row.get("usd") is not None else None,
            details=row,
        )
        n.ensure_checked()
        return n

    @staticmethod
    def from_detail_row(owner: str, row: Dict[str, Any]) -> "ClmmNFT":
        """
        Accepts a rich detail row (recommended):
          {
            poolPk, posMint, mintA, mintB,
            amountA, amountB, priceA, priceB,
            usd, inRange, tickLower, tickUpper, checked
          }
        """

        n = ClmmNFT(
            mint=str(row.get("posMint") or ""),
            owner=owner,
            pool_id=str(row.get("poolPk") or ""),
            token_a_mint=str(row.get("mintA") or "") or None,
            token_b_mint=str(row.get("mintB") or "") or None,
            amount_a=float(row["amountA"]) if row.get("amountA") is not None else None,
            amount_b=float(row["amountB"]) if row.get("amountB") is not None else None,
            price_a=float(row["priceA"]) if row.get("priceA") is not None else None,
            price_b=float(row["priceB"]) if row.get("priceB") is not None else None,
            usd_total=float(row["usd"]) if row.get("usd") is not None else None,
            in_range=bool(row["inRange"]) if row.get("inRange") is not None else None,
            tick_lower=int(row["tickLower"]) if row.get("tickLower") is not None else None,
            tick_upper=int(row["tickUpper"]) if row.get("tickUpper") is not None else None,
            checked_at=row.get("checked"),
            details=row,
        )
        n.ensure_checked()
        return n
