from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if (v is not None and v.strip() != "") else default


def _first_existing(paths: list[str | Path | None]) -> Optional[Path]:
    for p in paths:
        if not p:
            continue
        path = Path(p)
        if path.is_file():
            return path
    return None


def _load_json_config() -> tuple[Dict[str, Any], Optional[str]]:
    """
    Search order:
      1) AAVE_CONFIG_PATH (env)
      2) ./config/aave_config.json
      3) ./aave_config.json
    Returns (config_dict, path_str|None)
    """
    candidates: list[str | Path | None] = [
        _env("AAVE_CONFIG_PATH"),
        Path("config") / "aave_config.json",
        Path("aave_config.json"),
    ]
    path = _first_existing(candidates)
    if not path:
        return {}, None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("root JSON must be an object")
        return data, str(path)
    except Exception as e:  # noqa: BLE001
        log.warning("Failed to load Aave JSON config at %s: %s", path, e)
        return {}, str(path)


@dataclass(frozen=True)
class AaveConfig:
    """Runtime config for Aave integrations (Polygon by default)."""

    # —— Required for reads (GraphQL) ——
    chain_id: int                   # e.g. 137 for Polygon mainnet
    graphql_url: str                # Aave V3 GraphQL endpoint

    # —— Needed for writes (tx send); optional for reads ——
    evm_rpc_url: str                # Polygon RPC (can be 'MISSING' if not set)

    # —— Tunables ——
    http_timeout_sec: int = 25

    # —— Optional helper addresses if you choose on-chain data reads ——
    ui_pool_data_provider: Optional[str] = None
    protocol_data_provider: Optional[str] = None
    pool_address_provider: Optional[str] = None

    # —— Debug ——
    source_json_path: Optional[str] = None  # where we loaded JSON from (if any)

    @staticmethod
    def from_env() -> "AaveConfig":
        """
        Layering (highest → lowest):
          1) Process env vars
          2) aave_config.json (see search order above)
          3) Safe defaults (chain_id=137)
        JSON shape (example):
        {
          "aave": {
            "graphql_url": "https://api.v3.aave.com/graphql",
            "rpc_url": "https://polygon-rpc.com",
            "chain_id": 137,
            "http_timeout_sec": 25
          },
          "addresses": {
            "ui_pool_data_provider": null,
            "protocol_data_provider": null,
            "pool_address_provider": null
          }
        }
        """
        jcfg, jpath = _load_json_config()
        aave = jcfg.get("aave", {}) if isinstance(jcfg.get("aave", {}), dict) else {}
        addrs = jcfg.get("addresses", {}) if isinstance(jcfg.get("addresses", {}), dict) else {}

        chain_id = int(_env("AAVE_CHAIN_ID", str(aave.get("chain_id", 137))))
        graphql = _env("AAVE_GRAPHQL_URL", aave.get("graphql_url"))
        rpc = (
            _env("EVM_RPC_URL")
            or aave.get("rpc_url")
            or _env("POLYGON_RPC_URL")
        )
        timeout = int(_env("AAVE_HTTP_TIMEOUT_SEC", str(aave.get("http_timeout_sec", 25))))

        if not graphql:
            raise RuntimeError(
                "AAVE_GRAPHQL_URL is not set in env or aave_config.json. "
                "Provide the official Aave V3 GraphQL endpoint."
            )

        evm_rpc_url = rpc if rpc else "MISSING"

        return AaveConfig(
            chain_id=chain_id,
            graphql_url=graphql,
            evm_rpc_url=evm_rpc_url,
            http_timeout_sec=timeout,
            ui_pool_data_provider=addrs.get("ui_pool_data_provider"),
            protocol_data_provider=addrs.get("protocol_data_provider"),
            pool_address_provider=addrs.get("pool_address_provider"),
            source_json_path=jpath,
        )
