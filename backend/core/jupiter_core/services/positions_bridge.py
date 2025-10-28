from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from ..config import JupiterConfig, get_config


class PositionsBridge:
    """Bridge into PositionCore via DataLocker."""

    def __init__(self, cfg: Optional[JupiterConfig] = None) -> None:
        self.cfg = cfg or get_config()

    # -- internals -----------------------------------------------------
    def _dl(self):
        """Return the shared DataLocker instance respecting MOTHER_DB_PATH."""
        # Lazy import to avoid circular imports at module load time.
        from backend.data.data_locker import DataLocker  # type: ignore

        db_path = os.getenv("MOTHER_DB_PATH", self.cfg.mother_db_path)
        return DataLocker.get_instance(db_path)

    def _position_core(self, dl):
        from backend.core.positions_core.position_core import PositionCore  # type: ignore

        return PositionCore(dl)

    def _extract_pubkey(self, value: str) -> str:
        """Normalize a wallet address using the repo helper when available."""
        try:
            from backend.utils.pubkey import extract_pubkey  # type: ignore

            return extract_pubkey(value) or ""
        except Exception:
            cleaned = (value or "").strip()
            return cleaned.split()[0].split("?")[0].split("#")[0]

    # -- public --------------------------------------------------------
    def list_active_positions(
        self, *, owner_pubkey: Optional[str] = None, sync_if_empty: bool = False
    ) -> Dict[str, Any]:
        """Return PositionCore ACTIVE positions with optional filtering."""
        dl = self._dl()
        pc = self._position_core(dl)

        def _all_active() -> List[Dict[str, Any]]:
            rows = pc.get_active_positions() or []
            return [dict(row) for row in rows]

        filtered_by = None
        synced = False

        rows = _all_active()
        if owner_pubkey:
            try:
                want = owner_pubkey.strip()
                if want:
                    want = self._extract_pubkey(want)
                wallets = dl.read_wallets() or []
                match = None
                for wallet in wallets:
                    raw = str(wallet.get("public_address") or "").strip()
                    if not raw:
                        continue
                    if self._extract_pubkey(raw) == want:
                        match = wallet
                        break
                if match:
                    filtered_by = match.get("name") or match.get("wallet_name")
                    if filtered_by:
                        rows = [
                            row
                            for row in rows
                            if (row.get("wallet_name") or row.get("wallet")) == filtered_by
                        ]
            except Exception:
                pass

        if not rows and sync_if_empty:
            try:
                pc.update_positions_from_jupiter(source="jupiter_console")
                synced = True
                rows = _all_active()
                if filtered_by:
                    rows = [
                        row
                        for row in rows
                        if (row.get("wallet_name") or row.get("wallet")) == filtered_by
                    ]
            except Exception:
                synced = False

        return {"positions": rows, "filtered_by": filtered_by, "synced": synced}
