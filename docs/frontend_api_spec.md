# Frontend API Specification

This document describes the wrapper functions found under `frontend/src/api/`. These modules provide simple hooks and helper methods that communicate with the FastAPI backend via `axios` and `swr`.

## Overview

Each file in `frontend/src/api` exports React hooks or async functions for interacting with a specific backend route group. They rely on the utility `utils/axios.js` which exposes a configured `axios` instance and a `fetcher` function compatible with the `swr` data fetching library.

The sections below summarise the exports of each module and the network requests they perform.

## `alertThresholds.js`

Endpoints constants:

- `list` → `/alert_thresholds/`
- `bulk` → `/alert_thresholds/bulk`

Exports:

- **`getAllThresholds()`** – `GET` request to `list`. Returns the JSON body of all alert thresholds.
- **`saveAllThresholds(config)`** – `PUT` request to `bulk` replacing the entire configuration with `config`.
- **`createThreshold(payload)`** – `POST` to `list` creating a single threshold. Payload matches the backend `AlertThreshold` model.

Source excerpt:
```
import axios from 'utils/axios';
const endpoints = {
  list: '/alert_thresholds/',
  bulk: '/alert_thresholds/bulk'
};
```

## `cyclone.js`

Provides helpers to trigger maintenance tasks on the backend. All functions catch errors and re‑throw them after logging.

Exports:

- **`runFullCycle()`** – `POST /cyclone/run` to start the full Cyclone process.
- **`runPriceUpdate()`** – `POST /cyclone/prices` to update market prices.
- **`runPositionUpdate()`** – `POST /cyclone/positions` to refresh positions.
- **`deleteAllData()`** – `DELETE /cyclone/data` to wipe stored data.

Example implementation:
```
export async function runFullCycle() {
  try {
    return await axios.post('/cyclone/run');
  } catch (error) {
    console.error(error);
    throw error;
  }
}
```

## `menu.js`

Uses `swr` to fetch menu configuration from the backend and to store local UI state.

Constants:
- `key` – SWR cache key prefix `api/menu`.
- `master` – endpoint for local master state.
- `widget` – `/widget` path returning menu items.

Exports:

- **`useGetMenu()`** – SWR hook fetching `key + widget` via `fetcher`. Returns a memoized object with `menu`, loading/error flags and an empty check.
- **`useGetMenuMaster()`** – SWR hook providing a master state object `{ isDashboardDrawerOpened }` stored under `key + master`.
- **`handlerDrawerOpen(isDashboardDrawerOpened)`** – Helper that mutates the master state cache to toggle the dashboard drawer.

## `monitorStatus.js`

Fetches monitor health summaries.

Constants: `summary` → `/monitor_status/`.

Exports:

- **`useGetMonitorStatus()`** – SWR hook hitting `summary` and exposing `monitorStatus`, loading and error flags.
- **`refreshMonitorStatus()`** – Calls `mutate(summary)` to revalidate the SWR cache.
- `endpoints` – exported for convenience in other modules.

## `portfolio.js`

Interacts with portfolio history endpoints.

Constants:
- `latest` → `/portfolio/latest`
- `history` → `/portfolio/`

Exports:

- **`useGetLatestPortfolio()`** – SWR hook retrieving the most recent portfolio snapshot.
- **`useGetPortfolioHistory()`** – SWR hook returning the entire portfolio history array.
- **`refreshLatestPortfolio()`** – Mutates the `latest` cache key.
- **`refreshPortfolioHistory()`** – Mutates the `history` cache key.

Both hooks memoize the returned object containing data, error and loading fields plus an `historyEmpty` check for `useGetPortfolioHistory`.

## `positions.js`

Constants: `list` → `/positions/`.

Exports:

- **`useGetPositions(enabled = true)`** – SWR hook fetching all stored positions when `enabled` is truthy. Returns memoized data and status flags.
- **`refreshPositions()`** – `mutate(list)` to refresh the SWR cache.

## `traders.js`

Simple axios wrappers for CRUD operations on trader records.

Exports:

- **`getTraders()`** – `GET /traders` to list all traders.
- **`getTrader(name)`** – `GET /traders/{name}` for a single trader.
- **`createTrader(traderData)`** – `POST /traders` creating a new trader.
- **`updateTrader(name, traderData)`** – `PUT /traders/{name}` updating a trader.
- **`deleteTrader(name)`** – `DELETE /traders/{name}` removing a trader.

## `wallets.js`

Manages wallet resources and exposes a SWR hook similar to the other modules.

Constants:
- `list` → `/wallets/`
- `starWars` → `/wallets/star_wars`

Exports:

- **`useGetWallets(enabled = true)`** – SWR hook listing wallets. When `enabled` is `false`, the hook does not run.
- **`createWallet(wallet)`** – `POST` to `list` creating a wallet.
- **`updateWallet(name, wallet)`** – `PUT` to `list + encodeURIComponent(name)` updating a wallet.
- **`deleteWallet(name)`** – `DELETE` request to the same endpoint.
- **`insertStarWarsWallets()`** – `POST` to `starWars` inserting sample wallets.
- **`refreshWallets()`** – Mutate the SWR cache for `list`.

---

These utilities abstract away raw HTTP calls and allow React components to focus on rendering. They do not implement advanced error handling beyond console logging and rely on the backend documented in [backend_api_spec.md](backend_api_spec.md).
