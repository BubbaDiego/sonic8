import Grid from 'components/AppGrid';
import { useTheme } from '@mui/material/styles';
import { useEffect } from 'react';

import { ThemeMode } from 'config';

import StatusRail from 'ui-component/rails/StatusRail';
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
        <StatusRail
          totalValue={totalValue}
          heatIndex={heatIndexNumber}
          leverage={leverageNumber}
          totalSize={totalSizeNumber}
          isDark={isDark}
        />
      </Grid>
    </Grid>
  );
}
