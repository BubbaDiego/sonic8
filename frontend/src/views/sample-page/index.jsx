// material-ui

import Grid from '@mui/material/Grid';
import { useTheme } from '@mui/material/styles';
import { IconCurrencyDollar } from '@tabler/icons-react';
import TableChartOutlinedIcon from '@mui/icons-material/TableChartOutlined';

import { ThemeMode } from 'config';
import TotalValueCard from 'ui-component/cards/TotalValueCard';
import TotalLeverageDarkCard from 'ui-component/cards/TotalLeverageDarkCard';
import TotalLeverageLightCard from 'ui-component/cards/TotalLeverageLightCard';
import ValueToCollateralChartCard from 'ui-component/cards/charts/ValueToCollateralChartCard';
import { useGetLatestPortfolio } from 'api/portfolio';
import { useGetPositions } from 'api/positions';


// project imports
import MainCard from 'ui-component/cards/MainCard';

// ==============================|| SAMPLE PAGE ||============================== //

export default function SamplePage() {
  const theme = useTheme();
  const isDark = theme.palette.mode === ThemeMode.DARK;
  const { portfolio } = useGetLatestPortfolio();
  const shouldFetchPositions = portfolio == null;
  const { positions = [] } = useGetPositions(shouldFetchPositions);
  const fallbackTotal = positions.reduce(
    (sum, p) => sum + parseFloat(p.value || 0),
    0
  );
  const totalValueNumber = portfolio?.total_value ?? fallbackTotal;
  const totalValue = `$${Number(totalValueNumber || 0).toLocaleString()}`;

  return (
    <MainCard title="Sample Card">
      <Grid container spacing={2} columns={12}>
        <Grid sx={{ gridColumn: 'span 3' }}>
          <TotalValueCard
            primary="Total Value"
            secondary={totalValue}
            content="Yearly revenue"
            iconPrimary={IconCurrencyDollar}
            color="primary.main"
          />
        </Grid>
        <Grid sx={{ gridColumn: 'span 3' }}>
          {isDark ? (
            <TotalLeverageDarkCard />
          ) : (
            <TotalLeverageLightCard icon={<TableChartOutlinedIcon fontSize="inherit" />} />
          )}
        </Grid>

        <Grid sx={{ gridColumn: 'span 6' }}>
          <ValueToCollateralChartCard />
        </Grid>

      </Grid>
    </MainCard>
  );
}
