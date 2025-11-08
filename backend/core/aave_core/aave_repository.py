from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

log = logging.getLogger(__name__)

# Best-effort import; if DataLocker is unavailable in the dev shell,
# we degrade to writing JSON snapshots under reports/.
try:
    from backend.data.data_locker import DataLocker  # type: ignore
except Exception:  # noqa: BLE001
    DataLocker = None  # type: ignore[misc]


class AaveRepository:
    """Persist and retrieve Aave-derived snapshots in Sonic's storage."""

    def __init__(self):
        self._dl = DataLocker() if DataLocker else None
        self._fallback_dir = Path("reports")
        self._fallback_dir.mkdir(parents=True, exist_ok=True)

    def save_positions_snapshot(self, payload_positions: Dict[str, Any], source: str = "aave") -> None:
        if self._dl:
            try:
                # Convention: write into positions with a broker/source tag if your DataLocker supports it.
                self._dl.save("positions", {"source": source, **payload_positions})  # type: ignore[attr-defined]
                return
            except Exception as e:  # noqa: BLE001
                log.warning("DataLocker save failed, falling back to JSON: %s", e)
        # Fallback JSON
        Path(self._fallback_dir / "aave_positions.json").write_text(json.dumps(payload_positions, indent=2))

    def save_portfolio_snapshot(self, payload_portfolio: Dict[str, Any], source: str = "aave") -> None:
        if self._dl:
            try:
                self._dl.save("portfolio", {"source": source, **payload_portfolio})  # type: ignore[attr-defined]
                return
            except Exception as e:  # noqa: BLE001
                log.warning("DataLocker save failed, falling back to JSON: %s", e)
        Path(self._fallback_dir / "aave_portfolio.json").write_text(json.dumps(payload_portfolio, indent=2))
