import Grid from 'components/AppGrid';
import { useTheme } from '@mui/material/styles';
import { useEffect } from 'react';
import { IconCurrencyDollar } from '@tabler/icons-react';
import TableChartOutlinedIcon from '@mui/icons-material/TableChartOutlined';

import { ThemeMode } from 'config';
import TotalValueCard from 'ui-component/cards/TotalValueCard';
import TotalHeatIndexDarkCard from 'ui-component/cards/TotalHeatIndexDarkCard';
import TotalHeatIndexLightCard from 'ui-component/cards/TotalHeatIndexLightCard';
import TotalLeverageDarkCard from 'ui-component/cards/TotalLeverageDarkCard';
import TotalLeverageLightCard from 'ui-component/cards/TotalLeverageLightCard';
import TotalSizeDarkCard from 'ui-component/cards/TotalSizeDarkCard';
import TotalSizeLightCard from 'ui-component/cards/TotalSizeLightCard';
import PositionsTableCard from 'ui-component/cards/positions/PositionsTableCard';
import ValueToCollateralChartCard from 'ui-component/cards/charts/ValueToCollateralChartCard';
import { useGetLatestPortfolio, refreshLatestPortfolio } from 'api/portfolio';
import { useGetPositions, refreshPositions } from 'api/positions';
import { gridSpacing } from 'store/constant';

// ==============================|| OVERVIEW PAGE ||============================ //

export default function OverviewPage() {
  const theme = useTheme();
  const isDark = theme.palette.mode === ThemeMode.DARK;
  const { portfolio } = useGetLatestPortfolio();
  const shouldFetchPositions = portfolio == null;
  const { positions = [] } = useGetPositions(shouldFetchPositions);
  useEffect(() => {
    const id = setInterval(() => {
      refreshLatestPortfolio();
      refreshPositions();
    }, 60000);
    return () => clearInterval(id);
  }, []);
  const fallbackTotal = positions.reduce((sum, p) => sum + parseFloat(p.value || 0), 0);
  const totalValueNumber = portfolio?.total_value ?? fallbackTotal;
  const totalValue = `$${Number(totalValueNumber || 0).toLocaleString()}`;
  const heatIndexNumber = portfolio?.avg_heat_index ??
    (positions.length
      ? positions.reduce((sum, p) => sum + parseFloat(p.heat_index || 0) * (parseFloat(p.size || 1) || 1), 0) /
        positions.reduce((sum, p) => sum + (parseFloat(p.size || 1) || 1), 0)
      : 0);
  const fallbackSize = positions.reduce((s, p) => s + parseFloat(p.size || 0), 0);
  const fallbackLeverage =
    positions.length
      ?
          positions.reduce(
            (s, p) => s + parseFloat(p.leverage || 0) * parseFloat(p.size || 1),
            0
          ) / fallbackSize
      : 0;
  const totalSizeNumber = portfolio?.total_size ?? fallbackSize;
  const leverageNumber = portfolio?.avg_leverage ?? fallbackLeverage;

  return (
    <Grid container spacing={gridSpacing}>
      {/* ──────── Left column ──────── */}
      <Grid size={{ xs: 12, md: 8 }}>
        <Grid container spacing={gridSpacing}>
          <Grid size={12}>
            <PositionsTableCard />
          </Grid>
          <Grid size={12}>
            <ValueToCollateralChartCard />
          </Grid>
        </Grid>
      </Grid>

      {/* ──────── Right column ──────── */}
      <Grid size={{ xs: 12, md: 4 }}>
        <Grid container spacing={gridSpacing} direction="column">
          <Grid size="grow">
            <TotalValueCard
              primary="Total Value"
              secondary={totalValue}
              content="Yearly revenue"
              iconPrimary={IconCurrencyDollar}
              color="primary.main"
            />
          </Grid>
          <Grid size="grow">
            {isDark ? (
              <TotalHeatIndexDarkCard value={heatIndexNumber} />
            ) : (
              <TotalHeatIndexLightCard value={heatIndexNumber} icon={<TableChartOutlinedIcon fontSize="inherit" />} />
            )}
          </Grid>
          <Grid size="grow">
            {isDark ? (
              <TotalLeverageDarkCard value={leverageNumber} />
            ) : (
              <TotalLeverageLightCard value={leverageNumber} icon={<TableChartOutlinedIcon fontSize="inherit" />} />
            )}
          </Grid>
          <Grid size="grow">
            {isDark ? (
              <TotalSizeDarkCard value={totalSizeNumber} />
            ) : (
              <TotalSizeLightCard value={totalSizeNumber} icon={<TableChartOutlinedIcon fontSize="inherit" />} />
            )}
          </Grid>
        </Grid>
      </Grid>
    </Grid>
  );
}
