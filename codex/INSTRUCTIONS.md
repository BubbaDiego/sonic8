# Jupiter Page & API — CODΞX Handoff

This bundle adds a **Jupiter** page (3 tabs) and a FastAPI router that wraps Jupiter's Trigger API for **headless stop-loss** orders. Perps & Swaps tabs are placeholders you can extend later.

---

## What’s included

```
frontend/
  src/
    api/jupiter.js
    menu-items/jupiter.js
    views/jupiter/JupiterPage.jsx

backend/
  routes/jupiter_api.py
  services/jupiter_trigger.py
  services/signer_loader.py
  services/jupiter_perps.py   # stub
```

---

## 1) Frontend integration

1. **Sidebar menu**  
   Import the new item in `src/menu-items/index.js` and add it to the appropriate group:

   ```js
   // src/menu-items/index.js
   import jupiter from './jupiter';
   export default {
     items: [
       // ...existing groups/items
       jupiter, // put near Sonic Labs / Trader Factory
     ]
   };
   ```

2. **Route**  
   Add a route entry in `src/routes/MainRoutes.jsx` so `/jupiter` renders our page:

   ```jsx
   // src/routes/MainRoutes.jsx
   import Loadable from 'ui-component/Loadable';
   const JupiterPage = Loadable(lazy(() => import('views/jupiter/JupiterPage')));

   // inside MainRoutes children:
   {
     path: '/jupiter',
     element: <JupiterPage />
   },
   ```

   _Note:_ This follows your existing route pattern (React Router + Loadable).

3. **Client API**  
   The wrappers are in `src/api/jupiter.js`. They use your existing Axios client at `lib/api/sonicClient`.

4. **Styling**  
   The page uses existing `MainCard` and MUI components; it will match your theme and Notistack toasts.

---

## 2) Backend integration

1. **Router registration**  
   Register the router in `backend/sonic_backend_app.py`:

   ```py
   from backend.routes.jupiter_api import router as jupiter_router
   app.include_router(jupiter_router)
   ```

2. **Signer**  
   Put your Solana secret in `signer.txt` at the project **root**. Supported formats:
   - **Solana id.json** style array (64 integers)  
   - **Base64** 64‑byte secret (single line)

   Optional: set `SONIC_SIGNER_PATH=/absolute/path/to/signer.txt` if you store it elsewhere.

3. **Python deps**  
   Add to `requirements.txt` if needed:

   ```txt
   fastapi
   pydantic
   requests
   solders==0.26.0
   solana==0.30.2
   ```

4. **Run**  

   ```bash
   uvicorn backend.sonic_backend_app:app --host 0.0.0.0 --port 5000 --reload
   ```

5. **Endpoints**

   - `POST /api/jupiter/trigger/create`
     ```json
     {
       "inputSymbol": "SOL",
       "outputSymbol": "USDC",
       "amount": 0.5,
       "stopPrice": 120,
       "slippageBps": 0,
       "expirySeconds": 3600,
       "sendMode": "execute" // or "rpc"
     }
     ```
     Response includes `order`, `requestId`, and broadcast result.

   - `GET /api/jupiter/trigger/orders?status=active` — lists active orders for the signer wallet.

   - `POST /api/jupiter/trigger/cancel`  
     ```json
     {"order": "<order id from list>"}
     ```

   - `POST /api/jupiter/perps/attach-trigger` — **501 placeholder** for now.

   - `GET /api/jupiter/perps/positions` — placeholder empty list.

---

## 3) Notes & Safety

- The backend signs **versioned transactions** server‑side with your signer from `signer.txt`. Secrets never touch the browser.
- `sendMode=execute` uses Jupiter’s `/execute` to broadcast; `sendMode=rpc` sends via your RPC (set `rpcUrl`). 
- The frontend shows `makingAmount/takingAmount` preview to reduce fat‑finger mistakes. Always test with tiny size.
- Mint/decimal map currently includes **SOL** and **USDC**. Extend `MINTS` in `backend/services/jupiter_trigger.py` and `TOKENS` in the UI if you need more.
- Perps tab is a **scaffold**. When ready, we’ll wire Anchor/IDL calls in `backend/services/jupiter_perps.py` and add real UI.

---

## 4) Smoke test

1. Backend running with router registered and `signer.txt` present.
2. Navigate to **Jupiter** in the sidebar → “Spot Triggers” tab.
3. Submit: `SOL → USDC`, amount `0.01`, stop `50`, mode `Execute via Jupiter`.
4. You should see a success toast and the order appear in **Active Spot Triggers**.
5. Hit **Cancel** on the row to test cancel endpoint.

---

## 5) Future hooks

- Add a small **status chip** row (RPC health, wallet, keeper ping) at the top — data endpoint TBD.
- Perps: store attached triggers in your DB via DataLocker if you want local history/auditing.
- Swaps: use Jupiter `/quote` + `/swap` with server‑side signing similar to Trigger.
