// material-ui
import { useTheme } from '@mui/material/styles';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';

// project imports
import ValueToCollateralChartCard from './ValueToCollateralChartCard';
import LatestCustomerTableCard from './LatestCustomerTableCard';
import PortfolioTableCard from './PortfolioTableCard';
import { ThemeMode } from 'config';
import RevenueCard from 'ui-component/cards/RevenueCard';
import TotalValueCard from 'ui-component/cards/TotalValueCard';
import UserCountCard from 'ui-component/cards/UserCountCard';

import { gridSpacing } from 'store/constant';

// assets
import MonetizationOnTwoToneIcon from '@mui/icons-material/MonetizationOnTwoTone';
import AccountCircleTwoTone from '@mui/icons-material/AccountCircleTwoTone';
import DescriptionTwoToneIcon from '@mui/icons-material/DescriptionTwoTone';

// ==============================|| SONIC DASHBOARD ||============================== //

export default function Sonic() {
  const theme = useTheme();


  return (
    <Grid container spacing={gridSpacing}>
      <Grid size={{ xs: 12, lg: 8, md: 6 }}>
        <Grid container spacing={gridSpacing}>
          <Grid size={12}>
            <ValueToCollateralChartCard />
          </Grid>
          <Grid size={{ xs: 12, lg: 6 }}>
            <RevenueCard
              primary="Revenue"
              secondary="$42,562"
              content="$50,032 Last Month"
              iconPrimary={MonetizationOnTwoToneIcon}
              color="secondary.main"
            />
          </Grid>
          <Grid size={{ xs: 12, lg: 6 }}>
            <RevenueCard
              primary="Orders Received"
              secondary="486"
              content="20% Increase"
              iconPrimary={AccountCircleTwoTone}
              color="primary.main"
            />
          </Grid>
          <Grid size={12}>
            <LatestCustomerTableCard title="Latest Customers" />
          </Grid>
          <Grid size={12}>
            <PortfolioTableCard />
          </Grid>
        </Grid>
      </Grid>
      <Grid size={{ xs: 12, lg: 4, md: 6 }}>
        <Grid container spacing={gridSpacing}>
          <Grid size={12}>
            <TotalValueCard
              primary="Total Value"
              secondary="$0"
              content="1000 Shares"
              iconPrimary={MonetizationOnTwoToneIcon}
              color="secondary.main"
            />
          </Grid>
          <Grid size={12}>
            <UserCountCard primary="Daily user" secondary="1,658" iconPrimary={AccountCircleTwoTone} color="secondary.main" />
          </Grid>
          <Grid size={12}>
            <UserCountCard primary="Daily page view" secondary="1K" iconPrimary={DescriptionTwoToneIcon} color="primary.main" />
          </Grid>
        </Grid>
      </Grid>
    </Grid>
  );
}