from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

#from ..infrastructure.stores import AlertLogStore
#from backend.data.alert import AlertLog
from datetime import datetime


class ConfigError(Exception):
    pass


def load_thresholds(path: str | Path, log_store: AlertLogStore | None = None) -> Dict[str, Any]:
    path = Path(path)
    if not path.exists():
        if log_store:
            log_store.append(
                AlertLog(
                    id=str(datetime.utcnow().timestamp()),
                    alert_id=None,
                    phase="CONFIG",
                    level="ERROR",
                    message=f"missing config {path}",
                    payload=None,
                    timestamp=datetime.utcnow(),
                )
            )
        raise ConfigError(str(path))
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data
