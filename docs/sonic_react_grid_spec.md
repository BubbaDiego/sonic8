# Sonic React Grid Spec (v1)

## Stack prerequisites

- React ≥ 18
- @mui/material v6-alpha (or wrap the size prop as described)
- @emotion/react & @emotion/styled
- Sonic design tokens (palette, spacing) exported from `theme.js`

## 1. Conceptual model

```css
<Grid container>  ⟶   flexbox row   (spacing, columns, wrap, gap)
  <Grid item>     ⟶   flexbox child (size, grow, shrink, order)
    <GridItem/>   ⟶   styled Paper  (visual demo only)
```

`size` is our project-level alias for MUI’s breakpoint props (`xs|sm|md|lg|xl`).
The alias accepts three forms:

| Form   | Example                  | Meaning                                                |
|-------|-------------------------|--------------------------------------------------------|
| number | `size={6}`              | Divide the parent’s column count by N (defaults to 12) |
| object | `size={{ xs: 6, md: 4 }}` | Responsive sizes per breakpoint                        |
| "grow" | `size="grow"`           | Set `flexGrow: 1`, letting the cell fill remaining space |

**Edge case:** When using "grow" inside an object (`{ sm: "grow" }`) you must implement a small shim to translate that into (`flexGrow && flexBasis`). See “Mapping the size prop” in §8.

## 2. Component catalogue

| Component          | Purpose                                                         | File             |
|--------------------|-----------------------------------------------------------------|------------------|
| GridItem           | Low-level demo cell (Paper) holding placeholder content.        | GridItem.jsx GridItem |
| BasicGrid          | Showcase of fixed-column math (8 + 4 / 4 + 8).                  | BasicGrid.jsx BasicGrid |
| MultipleBreakPoints| Responsive swap between 6/6 → 8/4 layouts.                   | MultipleBreakPoints.jsx MultipleBreakPoints |
| SpacingGrid        | Runtime-adjustable spacing demo with radio buttons.             | SpacingGrid.jsx SpacingGrid |
| AutoGrid           | “Fluid-fixed-fluid” pattern using "grow" columns.            | AutoGrid.jsx AutoGrid |
| ColumnsGrid        | Overrides default 12-column grid with `columns={16}`.           | ColumnsGrid.jsx ColumnsGrid |
| NestedGrid         | Three identical form rows built with nested containers.         | NestedGrid.jsx NestedGrid |
| ComplexGrid        | Mini product card mixing image, text stack, and price.          | ComplexGrid.jsx ComplexGrid |
| GridSystem         | Gallery page that renders every demo in two-wide layout.        | index.jsx index |

The subsections below deep-dive into implementation details, extension points, and common pitfalls for each component.

## 3. Detailed component breakdown

### 3.1 GridItem

| Aspect      | Detail                                                                 |
|-------------|------------------------------------------------------------------------|
| Renders     | `<Paper elevation={0}>` with theme-driven typography.                  |
| Theme hooks | `theme.typography.body2.*`, `theme.spacing(1)`, `theme.palette.secondary.*`. |
| Why keep it | Central place to tweak demo visuals (e.g. change background to `primary.light` without touching the eight demos). |
| Prod spin-off | Rename to CardShell, pass children, and use for dashboard widgets. |

### 3.2 BasicGrid

Demonstrates the simplest 12-column arithmetic.

```jsx
<Grid container spacing={2}>
  <Grid size={8}> … </Grid>
  <Grid size={4}> … </Grid>
  <Grid size={4}> … </Grid>
  <Grid size={8}> … </Grid>
</Grid>
```

| Key ideas        | Implementation notes                                        |
|------------------|--------------------------------------------------------------|
| 12-column baseline | 8 + 4 + 4 + 8 sums to two rows of 12.                     |
| Spacing prop       | Hard-coded 2 shows default gap.                           |
| Novice gotcha      | Forgetting to wrap every `<Grid>` child with item semantics (`size` does this automatically). |

### 3.3 MultipleBreakPoints

Shows two-breakpoint override (`xs`, `md`).

| Pattern                       | Explanation                                   |
|-------------------------------|-----------------------------------------------|
| `size={{ xs: 6, md: 8 }}`     | Mobile half-width → Desktop two-thirds.    |
| `size={{ xs: 6, md: 4 }}`     | Complements the first cell: half → one-third. |
| Order independence            | Items are not re-ordered, merely resized; wrap to new line once total exceeds 12. |
| Extension                     | Add `{ lg: 3 }` to introduce third breakpoint with 16-column grid. |

### 3.4 SpacingGrid

Interactive control for the spacing prop.

| Feature             | How to replicate                                                        |
|---------------------|-------------------------------------------------------------------------|
| Stateful spacing    | `const [spacing, setSpacing] = useState(2);`                             |
| Radio → number     | On change, cast string → `Number()` before hand-off to MUI.          |
| Demo pattern        | Outermost grid sets `spacing={2}` for layout; inner showcase grid uses the reactive spacing. |
| Prod use            | Wrap in a Storybook knob to let designers test gutters globally.         |

### 3.5 AutoGrid

A “fluid-fixed-fluid” layout—classic for header / content / aside.

| Cell  | size value | Result                          |
|-------|------------|---------------------------------|
| Left  | "grow"     | `flexGrow: 1; flexBasis: 0`      |
| Center| 6          | Fixed half of 12 columns (on default 12 grid). |
| Right | "grow"     | Mirrors left column.             |

**Why prefer this over `CSS margin: 0 auto;`?**
Cells remain part of the flex row, allowing background colours or borders to span full height.

### 3.6 ColumnsGrid

| Highlight           | Detail                                                             |
|---------------------|--------------------------------------------------------------------|
| `columns={16}`      | Overrides default column count for this container only.            |
| Two children, both `size={8}` | Each occupies `8/16 = 50 %` of row width.                  |
| Use-case            | Porting Ant-Design or legacy PSDs that assume a 16-column grid.     |

### 3.7 NestedGrid

Reusable form rows via a nested container.

```jsx
function FormRow() {
  return (
    <>
      <Grid size={4}><Item/></Grid>
      <Grid size={4}><Item/></Grid>
      <Grid size={4}><Item/></Grid>
    </>
  );
}
```

| Best practice                        | Reason                                                                   |
|--------------------------------------|--------------------------------------------------------------------------|
| Extract inner rows into a function component (`FormRow`) | Keeps outer layout readable and lets you map over dynamic data. |
| `size={12}` on outer nested containers | Ensures each row consumes full width of parent before internal 3-col split. |

### 3.8 ComplexGrid

From demo → real product card in three steps.

| Region        | Implementation                                      | Notes                                                             |
|---------------|------------------------------------------------------|-------------------------------------------------------------------|
| Image         | `<ButtonBase><BannerImg src={banner}/></ButtonBase>` | ButtonBase gives focus ring & click ripple for free.              |
| Details stack | Second column with `direction="column" spacing={2}` | Holds title, meta, “Remove” action.                            |
| Price tag     | Third column with implicit width (auto in grid v6)   | Could be right-aligned with `sx={{ ml: 'auto' }}`.                |
| Wrapping      | Set outer grid `size={{ xs:12, sm:'grow' }}` so image stacks on mobile. |                                                              |
| Custom wrapper| The outermost `<SubCard>` adds a bordered card with padding—replace with your own `<Card variant="outlined">` in non-Sonic projects. |

### 3.9 GridSystem

| Responsibility             | Implementation                                                                       |
|----------------------------|--------------------------------------------------------------------------------------|
| Acts as living style-guide | Imports every demo component, wraps in `<MainCard title="…">`, lays them out two-up on `md` screens. |
| Depends on `gridSpacing` constant | Sourced from your Redux store (`store/constant`).                                      |
| Integration               | Mount under a route (`/grids`) so designers can verify that themes / palettes haven’t broken layout after updates. |

## 4. Size-prop shim (important!)

If you are not on MUI v6-alpha, create `AppGrid.jsx`:

```jsx
import Grid from '@mui/material/Grid';

export default function AppGrid({ size = 'grow', ...rest }) {
  // 1. Extract breakpoints or single value
  const translate = (val) => {
    if (val === 'grow') return { xs: true, sx: { flexGrow: 1, flexBasis: 0 } };
    if (typeof val === 'number') return { xs: val };
    if (typeof val === 'object') {
      return Object.fromEntries(
        Object.entries(val).map(([bp, v]) =>
          v === 'grow' ? [bp, true] : [bp, v]
        )
      );
    }
    return {};
  };

  const { xs, sm, md, lg, xl, sx: growSx } = translate(size);

  return (
    <Grid
      item
      xs={xs}
      sm={sm}
      md={md}
      lg={lg}
      xl={xl}
      sx={growSx}
      {...rest}
    />
  );
}
```

Replace every `import Grid from '@mui/material/Grid'` with `import Grid from 'components/AppGrid'`.
This guarantees "grow" works on all breakpoints and future MUI major versions.

## 5. Recommended folder structure

```cpp
src/
  components/
    grid/                      // ⬇ everything in this spec
      GridItem.jsx
      …
      index.jsx
    AppGrid.jsx                // size-prop shim (if needed)
  pages/
    GridShowcase.jsx           // simply re-exports GridSystem
  theme/
    palette.js
    typography.js
  store/
    constant.js                // exports gridSpacing
```

## 6. Common extension playbook

| Scenario                                 | Steps                                                                 |
|------------------------------------------|----------------------------------------------------------------------|
| Change default spacing                   | 1 → Update `gridSpacing` constant. 2 → Reload `/grids` to visually verify. |
| Add a new breakpoint (e.g. xl)           | Update theme breakpoints, then pass `size={{ xl: 3 }}` where needed. |
| Replace Item placeholders with real code | Grep for `<Item>` and substitute your new widget or form control—no layout changes required. |
| Globally switch to 16-column grid        | 1 → Wrap every container with `<Grid columns={16}>`. 2 → Adapt all hard-coded size numbers to new math. |
| Hide a column on mobile                  | Use `size={{ xs: 0, sm: 4 }}` (MUI treats 0 as `display: none;` in v6-alpha). |

## 7. FAQ

| Question                      | Answer                                                                                                                |
|-------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| Why not CSS Grid?             | MUI’s flexbox wrapper offers built-in theme spacing, breakpoints, RTL support, and automatic “stack on overflow” behaviour that designers expect from Bootstrap-like systems. |
| Can I nest containers indefinitely? | Yes, but deep trees hurt performance. Past three levels, consider splitting into separate components. |
| How do I animate re-order?    | Combine MUI Grid with `react-flip-toolkit`; sizes stay untouched.                                                     |
| Is "grow" performant?         | It translates to `flexGrow: 1; flexBasis: 0`, which is the canonical flexbox pattern—hardware accelerated on all evergreen browsers. |

## 8. Changelog template

Keep this at the bottom of `sonic_react_grid_spec.md` for future amendments.

```md
### YYYY-MM-DD – <author>

* <what changed and why>
```
