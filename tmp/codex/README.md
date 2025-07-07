    # Trader Shop Front‑End

    Generated on 2025-07-07.

    This package adds the **Trader Shop** feature to your Berry‑React frontend.

    ## Installation

    1. Copy the `src/` contents into your existing `frontend/src/` directory, preserving folder structure.
    2. Append the menu item from `src/menu-items/traderShop.js` to your `menu-items/index.js` (or import array).
    3. Register the route in `src/routes/index.jsx`:

       ```javascript
       import TraderShopRoutes from './TraderShopRoutes';
       // ...
       const routes = [AuthRoutes, DashboardRoutes, TraderShopRoutes];
       ```

    4. Run dev server:

       ```bash
       npm install
       npm run dev
       ```

    ## Files

    - src/views/traderShop/hooks.js
- src/views/traderShop/TraderFormDrawer.jsx
- src/views/traderShop/QuickImportStarWars.jsx
- src/views/traderShop/TraderShopList.jsx
- src/views/traderShop/index.jsx
- src/menu-items/traderShop.js
- src/routes/TraderShopRoutes.jsx

