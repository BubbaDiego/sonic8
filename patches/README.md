# Monitor Manager ‑ 2×2 layout refactor

This bundle defines a **clean 2 × 2 grid** for the dashboard and moves the size
controls into named constants so you can tweak dimensions quickly.

| Patch | Target | Highlights |
|-------|--------|------------|
| `MonitorManager.patch` | `src/pages/MonitorManager.jsx` | * Adds constants `ROW_A_HEIGHT`, `ROW_B_HEIGHT`, `COLUMN_B_START`, `GRID_GAP`.<br/>* Replaces the old `<Grid/>`‑based layout with a CSS‑grid based 2 × 2 card arrangement. |
| `ProfitMonitorCard.patch` | `src/components/ProfitMonitorCard.jsx` | Removes the per‑card enable/disable **Switch** (the Sonic Monitor now governs this). |

## Quick apply

```bash
unzip sonic_2x2_layout.zip -d /tmp/patches
cd <your‑repo>
git apply /tmp/patches/*.patch
```

The constants live at the top of **MonitorManager.jsx** – change the pixel
values to fine‑tune spacing or card sizes without hunting through JSX.

Generated 2025-07-29 22:56:53 UTC
