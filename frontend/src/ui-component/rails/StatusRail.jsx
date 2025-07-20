// src/ui-component/rails/StatusRail.jsx
import Grid from 'components/AppGrid';
import StatCard from 'components/StatusRail/StatCard';
import { gridSpacing } from 'store/constant';

export default function StatusRail({
  totalValue, heatIndex, leverage, totalSize, isDark
}) {
  return (
    <Grid
      container
      spacing={gridSpacing}
      direction="column"
      sx={{ position: 'sticky', top: 0 }}
    >
      <Grid size={12}>
        <StatCard
          variant={isDark ? 'dark' : 'light'}
          label="Value"
          value={totalValue}
        />
      </Grid>

      <Grid size={12}>
        <StatCard
          variant={isDark ? 'dark' : 'light'}
          label="Heat"
          value={heatIndex}
        />
      </Grid>

      <Grid size={12}>
        <StatCard
          variant={isDark ? 'dark' : 'light'}
          label="Leverage"
          value={leverage}
        />
      </Grid>

      <Grid size={12}>
        <StatCard
          variant={isDark ? 'dark' : 'light'}
          label="Size"
          value={totalSize}
        />
      </Grid>
    </Grid>
  );
}
