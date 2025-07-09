// index.jsx
import { useEffect, useState } from 'react';
import Grid from '@mui/material/Grid';
import MonitorSummaryCard from './MonitorSummaryCard';

// project imports
import MarketShareAreaChartCard from './PerformanceGraphCard';
import TraderListCard from './TraderListCard';
import PositionListCard from './PositionListCard';
import RevenueCard from 'ui-component/cards/RevenueCard';
import UserCountCard from 'ui-component/cards/UserCountCard';
import { useGetPositions } from 'api/positions';
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
  const { positions: positionsData } = useGetPositions();
  const [avgHeatIndex, setAvgHeatIndex] = useState(0);
  const [avgLeverage, setAvgLeverage] = useState(0);
  const [travelPercent, setTravelPercent] = useState(0);
  const [totalSize, setTotalSize] = useState(0);


  useEffect(() => {
    if (!positionsData && !portfolio) {
      return;
    }

    if (portfolio && typeof portfolio.avg_leverage === 'number') {
      setAvgLeverage(portfolio.avg_leverage);
    } else if (positionsData) {
      const weighted = positionsData.reduce(
        (sum, pos) => sum + (pos.leverage || 0) * (pos.size || 1),
        0
      );
      const size = positionsData.reduce((sum, pos) => sum + (pos.size || 0), 0);
      setAvgLeverage(size ? weighted / size : 0);
    }

    if (portfolio && typeof portfolio.avg_heat_index === 'number') {
      setAvgHeatIndex(portfolio.avg_heat_index);
    } else if (positionsData) {
      const heat = positionsData.reduce(
        (sum, pos) => sum + (pos.heat_index || 0),
        0
      );
      setAvgHeatIndex(positionsData.length ? heat / positionsData.length : 0);
    }

    if (positionsData) {
      const travel =
        positionsData.reduce((sum, pos) => sum + (pos.travel_percent || 0), 0) /
        positionsData.length;
      const size = positionsData.reduce((sum, pos) => sum + (pos.size || 0), 0);
      setTravelPercent(travel);
      setTotalSize(size);
    }
  }, [positionsData, portfolio]);

  return (
    <Grid container spacing={gridSpacing}>
      <Grid size={{ xs: 12, lg: 8, md: 6 }}>
        <Grid container spacing={gridSpacing}>
          <Grid size={12}>
            <PositionListCard title="Positions" />
          </Grid>
          <Grid size={12}>
            <MarketShareAreaChartCard />
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
              primary="Average Heat Index"
              secondary={avgHeatIndex.toFixed(2)}
              iconPrimary={WhatshotTwoToneIcon}
              color="error.main"
            />
          </Grid>
          <Grid size={12}>
            <UserCountCard
              primary="Average Leverage"
              secondary={avgLeverage.toFixed(2)}
              iconPrimary={SpeedTwoToneIcon}
              color="primary.main"
            />
          </Grid>
          <Grid size={{ xs: 12, lg: 12 }}>
            <RevenueCard
              primary="Travel Percent"
              secondary={`${travelPercent.toFixed(2)}%`}
              content="Current Avg. Travel %"
              iconPrimary={PercentTwoToneIcon}
              color="secondary.main"
            />
          </Grid>
          <Grid size={{ xs: 12, lg: 12 }}>
            <RevenueCard
              primary="Total Size"
              secondary={`${(totalSize / 1000).toFixed(1)}k`}
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
