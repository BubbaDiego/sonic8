# Full file: service façade the console/API can call.
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .gmx_runner import health as run_health, markets as run_markets, positions as run_positions


def get_health(cluster: str = "mainnet", signer_path: Optional[str] = None) -> Dict[str, Any]:
    return run_health(cluster=cluster, signer=signer_path)


def get_markets(cluster: str = "mainnet", signer_path: Optional[str] = None) -> List[Dict[str, Any]]:
    data = run_markets(cluster=cluster, signer=signer_path)
    return data.get("markets", [])


def get_positions(cluster: str = "mainnet", signer_path: Optional[str] = None) -> List[Dict[str, Any]]:
    data = run_positions(cluster=cluster, signer=signer_path)
    return data.get("positions", [])
