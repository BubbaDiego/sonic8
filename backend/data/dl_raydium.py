from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

from backend.models.nft import ClmmNFT
from backend.data.database import DatabaseManager  # same import path used by DataLocker


class DLRaydiumManager:
    """
    DB manager for Raydium NFTs (CLMM position NFTs).
    - Current state table: raydium_nfts
    - Time series table:  raydium_nft_history
    Provides simple, positions-like APIs:
      • upsert(), upsert_from_ts_payload()
      • get_by_owner(owner), get_by_mint(mint)
      • get_positions(owner=None)  (alias; returns NFT rows)
      • get_total_usd(owner=None)
      • history_for(mint, limit)
    """

    def __init__(self, db: DatabaseManager):
        self.db = db
        self._ensure_schema()

    # ── schema ─────────────────────────────────────────────────────────────────

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
        cur.execute("CREATE INDEX IF NOT EXISTS idx_rn_owner ON raydium_nfts(owner)")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_rn_hist_owner_time ON raydium_nft_history(owner, checked_at DESC)"
        )
        self.db.commit()

    # ── writers ────────────────────────────────────────────────────────────────

    def upsert(self, items: Iterable[ClmmNFT]) -> int:
        cur = self.db.get_cursor()
        if not cur:
            return 0

        count = 0
        for it in items:
            it.ensure_checked()
            details_json = json.dumps(it.details or {}, separators=(",", ":"), ensure_ascii=False)

            cur.execute(
                """
                INSERT INTO raydium_nfts
                    (nft_mint, owner, pool_id, token_a_mint, token_b_mint,
                     amount_a, amount_b, price_a, price_b, usd_total, in_range,
                     tick_lower, tick_upper, checked_at, source, details)
                VALUES
                    (:mint, :owner, :pool_id, :token_a_mint, :token_b_mint,
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
                    "mint": it.mint,
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
                    "checked_at": it.checked_at,
                    "source": it.source,
                    "details": details_json,
                },
            )

            # append to history
            cur.execute(
                """
                INSERT INTO raydium_nft_history
                    (nft_mint, owner, pool_id, amount_a, amount_b, price_a, price_b,
                     usd_total, checked_at, source, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    it.checked_at,
                    it.source,
                    details_json,
                ),
            )

            count += 1

        self.db.commit()
        return count

    def upsert_from_ts_payload(self, owner: str, payload: Dict[str, Any]) -> int:
        """
        Accepts TS helper output.
        Supports either:
          {"details":[...]} richer rows
        or  {"rows":[...]}    slim panel rows
        """

        items: List[ClmmNFT] = []
        if isinstance(payload.get("details"), list) and payload["details"]:
            for row in payload["details"]:
                items.append(ClmmNFT.from_detail_row(owner, row))
        elif isinstance(payload.get("rows"), list) and payload["rows"]:
            for row in payload["rows"]:
                items.append(ClmmNFT.from_panel_row(owner, row))
        else:
            return 0
        return self.upsert(items)

    # ── readers ────────────────────────────────────────────────────────────────

    def get_by_mint(self, nft_mint: str) -> Optional[Dict[str, Any]]:
        cur = self.db.get_cursor()
        if not cur:
            return None
        cur.execute("SELECT * FROM raydium_nfts WHERE nft_mint = ?", (nft_mint,))
        r = cur.fetchone()
        return dict(r) if r else None

    def get_by_owner(self, owner: str) -> List[Dict[str, Any]]:
        cur = self.db.get_cursor()
        if not cur:
            return []
        cur.execute(
            "SELECT * FROM raydium_nfts WHERE owner = ? ORDER BY COALESCE(usd_total,0) DESC",
            (owner,),
        )
        return [dict(x) for x in cur.fetchall()]

    # alias for “positions-style” API that panels/services expect
    def get_positions(self, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        cur = self.db.get_cursor()
        if not cur:
            return []
        if owner:
            cur.execute(
                "SELECT * FROM raydium_nfts WHERE owner = ? ORDER BY COALESCE(usd_total,0) DESC",
                (owner,),
            )
        else:
            cur.execute("SELECT * FROM raydium_nfts ORDER BY COALESCE(usd_total,0) DESC")
        return [dict(x) for x in cur.fetchall()]

    def list(self) -> List[Dict[str, Any]]:
        return self.get_positions()

    def get_total_usd(self, owner: Optional[str] = None) -> float:
        cur = self.db.get_cursor()
        if not cur:
            return 0.0
        if owner:
            cur.execute("SELECT SUM(usd_total) FROM raydium_nfts WHERE owner = ?", (owner,))
        else:
            cur.execute("SELECT SUM(usd_total) FROM raydium_nfts")
        v = cur.fetchone()[0]
        try:
            return float(v or 0.0)
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
        return [dict(x) for x in cur.fetchall()]
