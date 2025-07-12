import { useEffect, useState } from 'react';
import Grid from '@mui/material/Grid';
import MarketShareAreaChartCard from 'views/dashboard/PerformanceGraphCard';
import TraderListCard from 'views/dashboard/TraderListCard';
import PositionListCard from 'views/dashboard/PositionListCard';
import StatusRail from 'ui-component/status-rail/StatusRail';
import { useGetPositions } from 'api/positions';
import { useGetLatestPortfolio } from 'api/portfolio';
import CompositionPieCard from 'views/dashboard/CompositionPieCard';
import { gridSpacing } from 'store/constant';

export default function Analytics() {
  const { portfolio } = useGetLatestPortfolio();
  const { positions: positionsData } = useGetPositions();
  const [avgHeatIndex, setAvgHeatIndex] = useState(0);
  const [avgLeverage, setAvgLeverage] = useState(0);
  const [travelPercent, setTravelPercent] = useState(0);
  const [totalSize, setTotalSize] = useState(0);

  useEffect(() => {
    if (!positionsData && !portfolio) return;

    if (portfolio && typeof portfolio.avg_leverage === 'number') {
      setAvgLeverage(portfolio.avg_leverage);
    }

    if (portfolio && typeof portfolio.avg_heat_index === 'number') {
      setAvgHeatIndex(portfolio.avg_heat_index);
    }

    if (positionsData) {
      const travel =
        positionsData.reduce((sum, pos) => sum + (pos.travel_percent || 0), 0) / positionsData.length;
      const size = positionsData.reduce((sum, pos) => sum + (pos.size || 0), 0);
      setTravelPercent(travel);
      setTotalSize(size);
    }
  }, [positionsData, portfolio]);

  return (
    <Grid container spacing={gridSpacing}>
      <Grid item xs={12}>
        <StatusRail />
      </Grid>

      <Grid item xs={12}>
        <PositionListCard title="Positions" />
      </Grid>

      <Grid item xs={12} lg={8} md={6}>
        <MarketShareAreaChartCard />
      </Grid>

      <Grid item xs={12} lg={4} md={6}>
        <TraderListCard title="Traders" />
      </Grid>

      <Grid item xs={12} md={4}>
        <CompositionPieCard />
      </Grid>
    </Grid>
  );
}
