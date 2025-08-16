# UI Contracts (React)

## Route Map
- `/` — Dashboard
- `/orders` — List/Create
- `/positions/:id` — Detail & Adjust
- `/alerts` — Notifications

## State & Data
- **Where truth lives:** Server; React query caches client-side.
- **API client:** `web/src/lib/api/sonicClient.ts` is the single export.
- **Error surfaces:** Toast on 4xx; modal on destructive actions.

## Components
- **Smart**: page-level containers (fetch, orchestrate)
- **Dumb**: presentational; prop-driven; no fetch

## API Client Surface (example)
```ts
// web/src/lib/api/sonicClient.ts
export const sonic = {
  orders: {
    list: (q) => GET('/orders', q),
    create: (p, idempKey) => POST('/orders', p, { idempotencyKey: idempKey }),
  },
  positions: {
    get: (id) => GET(`/positions/${id}`),
    adjust: (id, delta) => POST(`/positions/${id}/adjust`, { delta }),
  }
};
```
