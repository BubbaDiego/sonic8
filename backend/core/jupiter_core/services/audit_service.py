from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import JupiterConfig
from ..dl.dl_jupiter_log_manager import DLJupiterLogManager


def _resolve_db_path(cfg: JupiterConfig) -> Path:
    """Resolve the SQLite path used when DataLocker is unavailable."""

    return Path(cfg.mother_db_path)


class AuditService:
    """Audit logging helper for Jupiter interactions."""

    def __init__(self, cfg: JupiterConfig, locker: Any = None) -> None:
        self.cfg = cfg
        self.db_path = _resolve_db_path(cfg)
        self.manager = DLJupiterLogManager(locker=locker, db_path=self.db_path)
        self.manager.ensure_schema()

    def log(
        self,
        *,
        kind: str,
        status: str,
        request: Optional[Dict[str, Any]] = None,
        response: Optional[Dict[str, Any]] = None,
        signature: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        """Persist an audit record and return the inserted row id."""

        return self.manager.insert(
            kind=kind,
            status=status,
            request_json=json.dumps(request) if request is not None else None,
            response_json=json.dumps(response) if response is not None else None,
            signature=signature,
            notes=notes,
        )

    def tail(self, limit: int = 20):
        """Return the latest audit rows."""

        return self.manager.tail(limit=limit)
