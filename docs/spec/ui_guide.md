# Sonic UI Guide

This guide helps humans (and GPTs) understand the **React/Vite** frontend quickly.

## How to read this UI
1. Start with the **UI manifest**: `docs/spec/ui.manifest.yaml`
   - routes → pages → components
   - components → props → examples
2. Open the component files listed in the manifest for implementation details.
3. Use **design tokens** (colors, spacing, fonts) instead of hardcoding.

## Conventions
- **Pages** live in `frontend/src/pages/`, **shared components** in `frontend/src/components/`.
- Use **React Router v6** patterns (`<Routes> / <Route>`, or `createBrowserRouter`).
- Prefer composable components (table, cards, bars) vs. duplicating markup.
- Do *not* invent props; reuse the ones listed in the manifest or evolve them centrally.

## Design tokens
- Colors, spacing scale, and fonts live in `design_tokens` in the UI manifest.
- If you use Tailwind, tokens map to your tailwind theme values.

## Dev Quickstart
```bash[user_guide.md](user_guide.md)
cd frontend
npm install
npm run dev   # vite on http://127.0.0.1:5173
```

## Keeping the manifest fresh

Run `python backend/scripts/ui_sweeper.py` to scan routes/components.

Optional: run `python backend/scripts/ui_snapshots.py` to capture route screenshots into `docs/spec/ui_shots/`.

## Common patterns

- **Tables**: centralize in `PositionsTable` (or similar) and pass typed rows.
- **Status bars/cards**: keep presentational logic (formatting) inside the component.
- **Page layout**: pages compose a small number of shared components.
