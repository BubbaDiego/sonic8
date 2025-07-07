// index.jsx
import Grid from '@mui/material/Grid';
import MonitorSummaryCard from './MonitorSummaryCard';

// project imports
import MarketShareAreaChartCard from './PerformanceGraphCard';
import TraderListCard from './TraderListCard';
import PositionListCard from './PositionListCard';
import RevenueCard from 'ui-component/cards/RevenueCard';
import UserCountCard from 'ui-component/cards/UserCountCard';
import { useGetLatestPortfolio } from 'api/portfolio';

import { gridSpacing } from 'store/constant';

// assets
import PercentTwoToneIcon from '@mui/icons-material/PercentTwoTone';
import WhatshotTwoToneIcon from '@mui/icons-material/WhatshotTwoTone';
import ScaleTwoToneIcon from '@mui/icons-material/ScaleTwoTone';
import SpeedTwoToneIcon from '@mui/icons-material/SpeedTwoTone';

// ==============================|| ANALYTICS DASHBOARD ||============================== //

export default function Analytics() {
  const { portfolio } = useGetLatestPortfolio();

  const totalHeatIndex = portfolio?.avg_heat_index?.toFixed(2) || '0.00';
  const totalLeverage = portfolio?.avg_leverage?.toFixed(2) || '0.00';
  const travelPercent = portfolio?.avg_travel_percent?.toFixed(2) || '0.00';
  const totalSize = portfolio?.total_size || 0;

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
            <TraderListCard title="Traders" />
          </Grid>
          <Grid size={12}>
            <UserCountCard
              primary="Total Heat Index"
              secondary={totalHeatIndex}
              iconPrimary={WhatshotTwoToneIcon}
              color="error.main"
            />
          </Grid>
          <Grid size={12}>
            <UserCountCard
              primary="Total Leverage"
              secondary={totalLeverage}
              iconPrimary={SpeedTwoToneIcon}
              color="primary.main"
            />
          </Grid>
          <Grid size={{ xs: 12, lg: 12 }}>
            <RevenueCard
              primary="Travel Percent"
              secondary={`${travelPercent}%`}
              content="Current Avg. Travel %"
              iconPrimary={PercentTwoToneIcon}
              color="secondary.main"
            />
          </Grid>
          <Grid size={{ xs: 12, lg: 12 }}>
            <RevenueCard
              primary="Total Size"
              secondary={totalSize}
              content="Aggregate Size"
              iconPrimary={ScaleTwoToneIcon}
              color="primary.main"
            />
          </Grid>
        </Grid>
      </Grid>
    </Grid>
  );
}
