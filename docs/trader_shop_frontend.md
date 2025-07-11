# Trader Shop Front-End

This document describes how to integrate the **Trader Shop** feature into the Berry-React frontend. The original instructions were distributed with a temporary `tmp/codex` bundle that duplicated the source files now under `frontend/src/`.

## Installation

1. Copy the contents of `src/` from the bundle into your existing `frontend/src/` directory, preserving the folder structure.
2. Append the menu item from `src/menu-items/traderShop.js` to your `menu-items/index.js` (or import array).
3. Register the route in `src/routes/index.jsx`:

```javascript
import TraderShopRoutes from './TraderShopRoutes';
// ...
const routes = [AuthRoutes, DashboardRoutes, TraderShopRoutes];
```

4. Run the development server:

```bash
npm install
npm run dev
```

## Files

- `src/views/traderShop/hooks.js`
- `src/views/traderShop/TraderFormDrawer.jsx`
- `src/views/traderShop/QuickImportStarWars.jsx`
- `src/views/traderShop/TraderShopList.jsx`
- `src/views/traderShop/index.jsx`
- `src/menu-items/traderShop.js`
- `src/routes/TraderShopRoutes.jsx`
