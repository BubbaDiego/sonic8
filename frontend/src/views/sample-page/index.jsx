// material-ui
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';
import { IconCurrencyDollar } from '@tabler/icons-react';

import TotalValueCard from 'ui-component/cards/TotalValueCard';

// project imports
import MainCard from 'ui-component/cards/MainCard';

// ==============================|| SAMPLE PAGE ||============================== //

export default function SamplePage() {
  return (
    <MainCard title="Sample Card">
      <Grid container>
        <Grid item xs={3}>
          <TotalValueCard
            primary="Total Value"
            secondary="$500,000"
            content="Yearly revenue"
            iconPrimary={IconCurrencyDollar}
            color="primary.main"
          />
        </Grid>
      </Grid>
    </MainCard>
  );
}
