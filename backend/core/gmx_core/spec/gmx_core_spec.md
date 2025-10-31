# GMX Core — Phase 1 (Scaffold)

This package integrates GMX V2 into sonic7. It mirrors `jupiter_core` so the mental model stays consistent.

## Goals (Phase 1)
- Establish stable module layout.
- Provide a console to verify imports and config presence.
- No network calls or external dependencies yet.

## What comes next (Phase 2)
- Implement read-only clients:
  - `clients/gmx_rest_client.py` (REST V2 tickers/candles/tokens/markets)
  - `clients/gmx_reader_client.py` (on-chain "Reader"/DataStore views)
  - `clients/subsquid_client.py` (GraphQL for history/reconciliation)
- Map raw → normalized positions in `models/mappers.py`
- Write snapshots to DL via `dl/positions_writer.py`
- Expose `GMXPositionSource` consumable by Position Sync Service

## Config
`config/gmx_chains.yaml` is the single source for chain/rpc/hosts/addresses.
`config/markets_seeds.json` seeds known markets until discovery is implemented.

## Console
Run:
```bash
python -m backend.core.gmx_core.console.console --help
python -m backend.core.gmx_core.console.console ping
python -m backend.core.gmx_core.console.console config --show
python -m backend.core.gmx_core.console.console smoke
```

Folder Anchors

clients/ : protocol + infra clients (RPC/WS, REST, Subsquid, Router)

adapters/ : thin layers composing clients into strategy-friendly data

models/ : dataclasses/enums + mappers to normalized schema

services/ : orchestration surfaces used by Positions Core

dl/ : writers to Data Locker (positions, markets, funding)

indexers/ : event streams + reconciliation jobs

console/ : headless CLI to test the above

Non-Goals (Phase 1)

Trading/order execution, funding math, or networking. Those land in Phases 2–4.


---

### `backend/core/gmx_core/config/gmx_chains.yaml`
```yaml
# GMX Core chain configuration (Phase 1 placeholders)
# Phase 2+ will validate and load these values for live calls.

arbitrum:
  chain_id: 42161
  rpc:
    http: "ENV:ARB_HTTP_RPC"   # e.g., https://arb-mainnet.g.alchemy.com/v2/<key>
    ws:   "ENV:ARB_WS_RPC"     # e.g., wss://arb-mainnet.g.alchemy.com/v2/<key>
  rest_hosts:
    - "https://arbitrum-api.gmxinfra.io"
    - "https://arbitrum-api.gmxinfra.net"      # fallback example
  subsquid_url: "https://squid-arb.gmxinfra.io/graphql"  # placeholder
  contracts:
    exchange_router: "0xEXCHANGE_ROUTER"    # fill at Phase 2
    reader:          "0xREADER"
    datastore:       "0xDATASTORE"
    order_vault:     "0xORDER_VAULT"
    event_emitter:   "0xEVENT_EMITTER"
  tokens:
    weth: "0xWETH"
    usdc: "0xUSDC"

avalanche:
  chain_id: 43114
  rpc:
    http: "ENV:AVAX_HTTP_RPC"
    ws:   "ENV:AVAX_WS_RPC"
  rest_hosts:
    - "https://avalanche-api.gmxinfra.io"
    - "https://avalanche-api.gmxinfra.net"
  subsquid_url: "https://squid-avax.gmxinfra.io/graphql" # placeholder
  contracts:
    exchange_router: "0xEXCHANGE_ROUTER"
    reader:          "0xREADER"
    datastore:       "0xDATASTORE"
    order_vault:     "0xORDER_VAULT"
    event_emitter:   "0xEVENT_EMITTER"
  tokens:
    wavax: "0xWAVAX"
    usdc:  "0xUSDC"
```
