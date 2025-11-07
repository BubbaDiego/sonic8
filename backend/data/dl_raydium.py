from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from backend.data.database import DatabaseManager

# Optional: keep the thin Core facade you already had
try:
    from backend.core.raydium_core.raydium_core import RaydiumCore
    from backend.core.raydium_core.rpc import SolanaRPC
    from backend.core.raydium_core.raydium_api import RaydiumApi
except Exception:  # pragma: no cover
    RaydiumCore = None
    SolanaRPC = None
    RaydiumApi = None


# ────────────────────────────────────────────────────────────────────────────────
# Models
# ────────────────────────────────────────────────────────────────────────────────

@dataclass
class NFT:
    """Generic NFT concept."""
    mint: str
    owner: Optional[str] = None
    standard: Optional[str] = None  # "SPL" | "Token-2022" | None
    name: Optional[str] = None
    collection: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClmmNFT(NFT):
    """Raydium CLMM position NFT."""
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
    source: str = "sdk+jupiter"
    details: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_detail_row(owner: str, row: Dict[str, Any]) -> "ClmmNFT":
        """
        Accepts a 'detail' style row from the TS helper:
        {
          poolPk, posMint, tokenA_amount, tokenB_amount,
          mintA, mintB, priceA, priceB, usd, inRange, tickLower, tickUpper, ...
        }
        """
        now = datetime.now(timezone.utc).isoformat()
        return ClmmNFT(
            mint=str(row.get("posMint")),
            owner=owner,
            pool_id=str(row.get("poolPk")),
            token_a_mint=str(row.get("mintA")) if row.get("mintA") else None,
            token_b_mint=str(row.get("mintB")) if row.get("mintB") else None,
            amount_a=float(row.get("amountA")) if row.get("amountA") is not None else None,
            amount_b=float(row.get("amountB")) if row.get("amountB") is not None else None,
            price_a=float(row.get("priceA")) if row.get("priceA") is not None else None,
            price_b=float(row.get("priceB")) if row.get("priceB") is not None else None,
            usd_total=float(row.get("usd")) if row.get("usd") is not None else None,
            in_range=bool(row.get("inRange")) if row.get("inRange") is not None else None,
            tick_lower=int(row.get("tickLower")) if row.get("tickLower") is not None else None,
            tick_upper=int(row.get("tickUpper")) if row.get("tickUpper") is not None else None,
            checked_at=row.get("checked") or now,
            details=row,
        )

    @staticmethod
    def from_panel_row(owner: str, row: Dict[str, Any]) -> "ClmmNFT":
        """
        Accepts the simpler 'panelRows' form:
        { name, address, chain, usd, checked }
        """
        now = datetime.now(timezone.utc).isoformat()
        return ClmmNFT(
            mint=str(row.get("address")),
            owner=owner,
            usd_total=float(row.get("usd")) if row.get("usd") is not None else None,
            checked_at=row.get("checked") or now,
            details=row,
        )


# ────────────────────────────────────────────────────────────────────────────────
# Manager
# ────────────────────────────────────────────────────────────────────────────────

class DLRaydiumManager:
    """
    DB manager for Raydium NFTs (CLMM position NFTs).
    - Upsert current valuation to `raydium_nfts`
    - Append history to `raydium_nft_history`
    - Query by owner/mint and compute totals
    """

    def __init__(self, db: DatabaseManager):
        self.db = db
        self._ensure_schema()

    # ----- schema ---------------------------------------------------------------

    def _ensure_schema(self) -> None:
        cur = self.db.get_cursor()
        if not cur:
            return

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS raydium_nfts (
                nft_mint        TEXT PRIMARY KEY,
                owner           TEXT,
                pool_id         TEXT,
                token_a_mint    TEXT,
                token_b_mint    TEXT,
                amount_a        REAL,
                amount_b        REAL,
                price_a         REAL,
                price_b         REAL,
                usd_total       REAL,
                in_range        INTEGER,
                tick_lower      INTEGER,
                tick_upper      INTEGER,
                checked_at      TEXT,
                source          TEXT,
                details         TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS raydium_nft_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                nft_mint        TEXT,
                owner           TEXT,
                pool_id         TEXT,
                amount_a        REAL,
                amount_b        REAL,
                price_a         REAL,
                price_b         REAL,
                usd_total       REAL,
                checked_at      TEXT,
                source          TEXT,
                details         TEXT
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_rn_owner ON raydium_nfts(owner)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_rn_hist_owner_time ON raydium_nft_history(owner, checked_at DESC)"
        )
        self.db.commit()

    # ----- writers --------------------------------------------------------------

    def upsert(self, items: Iterable[ClmmNFT]) -> int:
        """Upsert current rows and append to history."""
        cur = self.db.get_cursor()
        if not cur:
            return 0

        count = 0
        for it in items:
            js = json.dumps(it.details or {}, separators=(",", ":"), ensure_ascii=False)
            cur.execute(
                """
                INSERT INTO raydium_nfts
                    (nft_mint, owner, pool_id, token_a_mint, token_b_mint,
                     amount_a, amount_b, price_a, price_b, usd_total, in_range,
                     tick_lower, tick_upper, checked_at, source, details)
                VALUES
                    (:nft_mint, :owner, :pool_id, :token_a_mint, :token_b_mint,
                     :amount_a, :amount_b, :price_a, :price_b, :usd_total, :in_range,
                     :tick_lower, :tick_upper, :checked_at, :source, :details)
                ON CONFLICT(nft_mint) DO UPDATE SET
                    owner=:owner,
                    pool_id=:pool_id,
                    token_a_mint=:token_a_mint,
                    token_b_mint=:token_b_mint,
                    amount_a=:amount_a,
                    amount_b=:amount_b,
                    price_a=:price_a,
                    price_b=:price_b,
                    usd_total=:usd_total,
                    in_range=:in_range,
                    tick_lower=:tick_lower,
                    tick_upper=:tick_upper,
                    checked_at=:checked_at,
                    source=:source,
                    details=:details
                """,
                {
                    "nft_mint": it.mint,
                    "owner": it.owner,
                    "pool_id": it.pool_id,
                    "token_a_mint": it.token_a_mint,
                    "token_b_mint": it.token_b_mint,
                    "amount_a": it.amount_a,
                    "amount_b": it.amount_b,
                    "price_a": it.price_a,
                    "price_b": it.price_b,
                    "usd_total": it.usd_total,
                    "in_range": 1 if it.in_range else 0 if it.in_range is not None else None,
                    "tick_lower": it.tick_lower,
                    "tick_upper": it.tick_upper,
                    "checked_at": it.checked_at or datetime.now(timezone.utc).isoformat(),
                    "source": it.source,
                    "details": js,
                },
            )
            cur.execute(
                """
                INSERT INTO raydium_nft_history
                    (nft_mint, owner, pool_id, amount_a, amount_b, price_a, price_b,
                     usd_total, checked_at, source, details)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    it.mint,
                    it.owner,
                    it.pool_id,
                    it.amount_a,
                    it.amount_b,
                    it.price_a,
                    it.price_b,
                    it.usd_total,
                    it.checked_at or datetime.now(timezone.utc).isoformat(),
                    it.source,
                    js,
                ),
            )
            count += 1

        self.db.commit()
        return count

    def upsert_from_ts_payload(self, owner: str, payload: Dict[str, Any]) -> int:
        """
        Accepts the TS helper's JSON line.
        Supports:
          { rows: [ panelRows... ] }
          { details: [ detailRows... ] }
        """
        items: List[ClmmNFT] = []
        details = payload.get("details")
        if isinstance(details, list) and details:
            for row in details:
                items.append(ClmmNFT.from_detail_row(owner, row))
        else:
            rows = payload.get("rows") or []
            for row in rows:
                items.append(ClmmNFT.from_panel_row(owner, row))
        return self.upsert(items)

    # ----- readers --------------------------------------------------------------

    def get_by_mint(self, nft_mint: str) -> Optional[Dict[str, Any]]:
        cur = self.db.get_cursor()
        if not cur:
            return None
        cur.execute("SELECT * FROM raydium_nfts WHERE nft_mint = ?", (nft_mint,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_by_owner(self, owner: str) -> List[Dict[str, Any]]:
        cur = self.db.get_cursor()
        if not cur:
            return []
        cur.execute(
            "SELECT * FROM raydium_nfts WHERE owner = ? ORDER BY usd_total DESC NULLS LAST",
            (owner,),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_total_usd(self, owner: Optional[str] = None) -> float:
        cur = self.db.get_cursor()
        if not cur:
            return 0.0
        if owner:
            cur.execute("SELECT SUM(usd_total) FROM raydium_nfts WHERE owner = ?", (owner,))
        else:
            cur.execute("SELECT SUM(usd_total) FROM raydium_nfts")
        val = cur.fetchone()[0]
        try:
            return float(val or 0.0)
        except Exception:
            return 0.0

    def history_for(self, nft_mint: str, limit: int = 100) -> List[Dict[str, Any]]:
        cur = self.db.get_cursor()
        if not cur:
            return []
        cur.execute(
            "SELECT * FROM raydium_nft_history WHERE nft_mint = ? ORDER BY checked_at DESC LIMIT ?",
            (nft_mint, int(limit)),
        )
        return [dict(r) for r in cur.fetchall()]


# Back-compat tiny facade (if used elsewhere)
class DLRaydiumCore:
    def __init__(self, rpc_url: Optional[str] = None):
        if RaydiumCore and SolanaRPC and RaydiumApi:
            self.core = RaydiumCore(rpc=SolanaRPC(rpc_url), api=RaydiumApi())
        else:
            self.core = None

    def get_owner_portfolio(self, owner: str):
        if not self.core:
            raise RuntimeError("RaydiumCore not available in this environment.")
        return self.core.load_owner_portfolio(owner)
