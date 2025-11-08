from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name, default)
    return v if v is None or v.strip() != "" else default


@dataclass(frozen=True)
class AaveConfig:
    """Runtime config for Aave integrations."""

    # —— Network / endpoints ——
    chain_id: int                   # e.g., 137 for Polygon mainnet
    graphql_url: str                # Aave V3 GraphQL endpoint (must be set)
    evm_rpc_url: str                # Polygon RPC for txs (writes) and fallbacks

    # —— Timeouts / knobs ——
    http_timeout_sec: int = 25

    # —— Optional: on-chain helpers (addresses) if skipping GraphQL for reads ——
    # If you want to use on-chain data providers, pass these via env or config.
    ui_pool_data_provider: str | None = None
    protocol_data_provider: str | None = None
    pool_address_provider: str | None = None

    @staticmethod
    def from_env() -> "AaveConfig":
        """
        Environment variables (document these in spec.manifest.yaml):
          - AAVE_CHAIN_ID           (default 137)
          - AAVE_GRAPHQL_URL        (required)
          - EVM_RPC_URL             (required for writes; good to have for reads)
          - AAVE_UI_POOL_DATA_PROVIDER (optional)
          - AAVE_PROTOCOL_DATA_PROVIDER (optional)
          - AAVE_POOL_ADDRESS_PROVIDER  (optional)
        """
        chain_id = int(_env("AAVE_CHAIN_ID", "137"))
        graphql = _env("AAVE_GRAPHQL_URL")
        rpc = _env("EVM_RPC_URL") or _env("POLYGON_RPC_URL")

        if not graphql:
            raise RuntimeError(
                "AAVE_GRAPHQL_URL is not set. Provide the official Aave V3 GraphQL endpoint for Polygon."
            )
        if not rpc:
            # reads can still work via GraphQL, but writes/health fallbacks will need RPC
            # keep this non-fatal; raise only when a write path is invoked.
            rpc = "MISSING"

        return AaveConfig(
            chain_id=chain_id,
            graphql_url=graphql,
            evm_rpc_url=rpc,
            http_timeout_sec=int(_env("AAVE_HTTP_TIMEOUT_SEC", "25") or "25"),
            ui_pool_data_provider=_env("AAVE_UI_POOL_DATA_PROVIDER"),
            protocol_data_provider=_env("AAVE_PROTOCOL_DATA_PROVIDER"),
            pool_address_provider=_env("AAVE_POOL_ADDRESS_PROVIDER"),
        )
