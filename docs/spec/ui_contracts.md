# UI Contracts

## Routes
- `/overview` – uses `portfolio` and `positions`
- `/positions` – uses `positions`
- `/wallet-manager` – uses `wallets`
- `/monitor-manager` – uses `sonicMonitor` and `monitorStatus`
- `/dashboard/analytics` – uses `portfolio` and `positions`
- `/communications/xcom` – uses `xcom`
- `/sonic` – uses `session`, `portfolio`, `positions`, and `traders`

## API Client
[frontend/src/lib/api/sonicClient.ts](../../frontend/src/lib/api/sonicClient.ts)
re-exports:

- `positions`
  - `useGetPositions`
  - `refreshPositions`
- `portfolio`
  - `useGetLatestPortfolio`
  - `useGetPortfolioHistory`
  - `refreshLatestPortfolio`
  - `refreshPortfolioHistory`
- `wallets`
  - `useGetWallets`
  - `createWallet`
  - `updateWallet`
  - `deleteWallet`
  - `insertStarWarsWallets`
  - `refreshWallets`

## Errors
- `401` → redirect to login
- `403` or `404` → in-page notice
- `409` → toast notification
- `422` or `400` → inline form errors
- `429` or `5xx` → modal with retry option
