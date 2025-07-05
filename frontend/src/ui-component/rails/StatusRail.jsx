// src/ui-component/rails/StatusRail.jsx
import Grid from 'components/AppGrid';
import { IconCurrencyDollar } from '@tabler/icons-react';
import TableChartOutlinedIcon from '@mui/icons-material/TableChartOutlined';

import TotalValueCard from 'ui-component/cards/TotalValueCard';
import TotalHeatIndexDarkCard from 'ui-component/cards/TotalHeatIndexDarkCard';
import TotalHeatIndexLightCard from 'ui-component/cards/TotalHeatIndexLightCard';
import TotalLeverageDarkCard from 'ui-component/cards/TotalLeverageDarkCard';
import TotalLeverageLightCard from 'ui-component/cards/TotalLeverageLightCard';
import TotalSizeDarkCard from 'ui-component/cards/TotalSizeDarkCard';
import TotalSizeLightCard from 'ui-component/cards/TotalSizeLightCard';
import { gridSpacing } from 'store/constant';

export default function StatusRail({
  totalValue, heatIndex, leverage, totalSize, isDark
}) {
  // Stick to top on any breakpoint ≥ md; normal flow on mobile.
  return (
    <Grid
      container
      spacing={gridSpacing}
      direction="column"
      sx={{ position: { md: 'sticky' }, top: { md: 0 } }}
    >
      <Grid size={{ xs: 12 }}>
        <TotalValueCard
          primary="Total Value"
          secondary={totalValue}
          content="Yearly revenue"
          iconPrimary={IconCurrencyDollar}
          color="primary.main"
        />
      </Grid>

      <Grid size={{ xs: 12 }}>
        {isDark
          ? <TotalHeatIndexDarkCard value={heatIndex} />
          : (
            <TotalHeatIndexLightCard
              value={heatIndex}
              icon={<TableChartOutlinedIcon fontSize="inherit" />}
            />
          )}
      </Grid>

      <Grid size={{ xs: 12 }}>
        {isDark
          ? <TotalLeverageDarkCard value={leverage} />
          : (
            <TotalLeverageLightCard
              value={leverage}
              icon={<TableChartOutlinedIcon fontSize="inherit" />}
            />
          )}
      </Grid>

      <Grid size={{ xs: 12 }}>
        {isDark
          ? <TotalSizeDarkCard value={totalSize} />
          : (
            <TotalSizeLightCard
              value={totalSize}
              icon={<TableChartOutlinedIcon fontSize="inherit" />}
            />
          )}
      </Grid>
    </Grid>
  );
}
