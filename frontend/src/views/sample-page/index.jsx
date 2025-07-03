// material-ui
import Grid from '@mui/material/Grid';
import { useTheme } from '@mui/material/styles';
import { IconCurrencyDollar } from '@tabler/icons-react';
import TableChartOutlinedIcon from '@mui/icons-material/TableChartOutlined';

import { ThemeMode } from 'config';
import TotalValueCard from 'ui-component/cards/TotalValueCard';
import TotalLeverageDarkCard from 'ui-component/cards/TotalLeverageDarkCard';
import TotalLeverageLightCard from 'ui-component/cards/TotalLeverageLightCard';

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
      </Grid>
    </MainCard>
  );
}
