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

// This sample demonstrates a TotalValueCard with a themed Total Leverage card
// that toggles between light and dark variants based on the current theme.

// project imports
import MainCard from 'ui-component/cards/MainCard';

// ==============================|| SAMPLE PAGE ||============================== //

export default function SamplePage() {
  const theme = useTheme();
  const isDark = theme.palette.mode === ThemeMode.DARK;

  return (
    <MainCard title="Sample Card">
      <Grid container spacing={2}>
        <Grid item xs={3}>
          <TotalValueCard
            primary="Total Value"
            secondary="$500,000"
            content="Yearly revenue"
            iconPrimary={IconCurrencyDollar}
            color="primary.main"
          />
        </Grid>
        <Grid item xs={3}>
          {isDark ? (
            <TotalLeverageDarkCard />
          ) : (
            <TotalLeverageLightCard icon={<TableChartOutlinedIcon fontSize="inherit" />} />
          )}
        </Grid>
        <Grid item xs={6}>
          <ValueToCollateralChartCard />
        </Grid>
      </Grid>
    </MainCard>
  );
}
