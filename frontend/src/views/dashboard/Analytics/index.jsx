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
import { getTraders } from 'api/traders';

import { gridSpacing } from 'store/constant';

// assets
import PercentTwoToneIcon from '@mui/icons-material/PercentTwoTone';
import WhatshotTwoToneIcon from '@mui/icons-material/WhatshotTwoTone';
import ScaleTwoToneIcon from '@mui/icons-material/ScaleTwoTone';
import SpeedTwoToneIcon from '@mui/icons-material/SpeedTwoTone';

// ==============================|| ANALYTICS DASHBOARD ||============================== //

export default function Analytics() {
  const { data: positionsData } = useGetPositions();
  const [totalHeatIndex, setTotalHeatIndex] = useState(0);
  const [totalLeverage, setTotalLeverage] = useState(0);
  const [travelPercent, setTravelPercent] = useState(0);
  const [totalSize, setTotalSize] = useState(0);

  useEffect(() => {
    const loadTraders = async () => {
      try {
        const traders = await getTraders();
        const heatIndex = traders.reduce((sum, trader) => sum + (trader.heat_index || 0), 0);
        setTotalHeatIndex(heatIndex);
      } catch (error) {
        console.error('Error fetching traders:', error);
      }
    };

    loadTraders();
  }, []);

  useEffect(() => {
    if (positionsData) {
      const leverage = positionsData.reduce((sum, pos) => sum + (pos.leverage || 0), 0);
      const travel = positionsData.reduce((sum, pos) => sum + (pos.travel_percent || 0), 0) / positionsData.length;
      const size = positionsData.reduce((sum, pos) => sum + (pos.size || 0), 0);

      setTotalLeverage(leverage);
      setTravelPercent(travel);
      setTotalSize(size);
    }
  }, [positionsData]);

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
              secondary={totalHeatIndex.toFixed(2)}
              iconPrimary={WhatshotTwoToneIcon}
              color="error.main"
            />
          </Grid>
          <Grid size={12}>
            <UserCountCard
              primary="Total Leverage"
              secondary={totalLeverage.toFixed(2)}
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
