// index.jsx
import Grid from '@mui/material/Grid';
import MonitorSummaryCard from './MonitorSummaryCard';

// project imports
import MarketShareAreaChartCard from './PerformanceGraphCard';
import TotalRevenueCard from './TotalRevenueCard';
import PositionListCard from './PositionListCard';
import RevenueCard from 'ui-component/cards/RevenueCard';
import UserCountCard from 'ui-component/cards/UserCountCard';

import { gridSpacing } from 'store/constant';

// assets
import PercentTwoToneIcon from '@mui/icons-material/PercentTwoTone';
import WhatshotTwoToneIcon from '@mui/icons-material/WhatshotTwoTone';
import ScaleTwoToneIcon from '@mui/icons-material/ScaleTwoTone';
import SpeedTwoToneIcon from '@mui/icons-material/SpeedTwoTone';

// ==============================|| ANALYTICS DASHBOARD ||============================== //

export default function Analytics() {
  return (
    <Grid container spacing={gridSpacing}>
      <Grid size={{ xs: 12, lg: 8, md: 6 }}>
        <Grid container spacing={gridSpacing}>
          <Grid size={12}>
            <MarketShareAreaChartCard />
          </Grid>
          <Grid size={12}>
            <PositionListCard title="Positions" />
          </Grid>
        </Grid>
      </Grid>

      <Grid size={{ xs: 12, lg: 4, md: 6 }}>
        <Grid container spacing={gridSpacing}>
          <Grid size={12}>
            <MonitorSummaryCard />
          </Grid>
          <Grid size={12}>
            <TotalRevenueCard title="Total Revenue" />
          </Grid>
          <Grid size={12}>
            <UserCountCard
              primary="Total Heat Index"
              secondary="1,658"
              iconPrimary={WhatshotTwoToneIcon}
              color="error.main"
            />
          </Grid>
          <Grid size={12}>
            <UserCountCard
              primary="Total Leverage"
              secondary="1K"
              iconPrimary={SpeedTwoToneIcon}
              color="primary.main"
            />
          </Grid>
          <Grid size={{ xs: 12, lg: 12 }}>
            <RevenueCard
              primary="Travel Percent"
              secondary="$42,562"
              content="$50,032 Last Month"
              iconPrimary={PercentTwoToneIcon}
              color="secondary.main"
            />
          </Grid>
          <Grid size={{ xs: 12, lg: 12 }}>
            <RevenueCard
              primary="Total Size"
              secondary="486"
              content="20% Increase"
              iconPrimary={ScaleTwoToneIcon}
              color="primary.main"
            />
          </Grid>
        </Grid>
      </Grid>
    </Grid>
  );
}
