import { useEffect, useState } from 'react';

// material-ui
import { useTheme } from '@mui/material/styles';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';

// third party
import Chart from 'react-apexcharts';

// project imports
import { ThemeMode } from 'config';
import useConfig from 'hooks/useConfig';
import MainCard from 'ui-component/cards/MainCard';
import { useGetPortfolioHistory } from 'api/portfolio';

// canned data for initial UI
const initialChartData = {
  series: [
    { name: 'Total Value', data: [] },
    { name: 'Total Collateral', data: [] }
  ],
  options: {
    chart: { type: 'area', height: 350 },
    colors: ['#4caf50', '#ff9800'],
    dataLabels: { enabled: false },
    stroke: { curve: 'smooth' },
    xaxis: { categories: [] },
    tooltip: { theme: 'light' },
    yaxis: {
      labels: {
        formatter: (value) => Math.round(value)
      }
    }
  }
};

// ===========================|| VALUE TO COLLATERAL CHART CARD ||=========================== //

export default function ValueToCollateralChartCard() {
  const theme = useTheme();
  const { mode } = useConfig();
  const [chartConfig, setChartConfig] = useState(initialChartData);
  const { history = [], historyLoading } = useGetPortfolioHistory();

  useEffect(() => {
    if (historyLoading) {
      return;
    }
    const categories = history.map((d) =>
      new Date(d.snapshot_time).toLocaleDateString()
    );
    const valueSeries = history.map((d) => parseFloat(d.total_value || 0));
    const collateralSeries = history.map((d) => parseFloat(d.total_collateral || 0));
    setChartConfig((prev) => ({
      ...prev,
      series: [
        { name: 'Total Value', data: valueSeries },
        { name: 'Total Collateral', data: collateralSeries }
      ],
      options: {
        ...prev.options,
        xaxis: { categories }
      }
    }));
  }, [history, historyLoading]);

  useEffect(() => {
    setChartConfig((prev) => ({
      ...prev,
      options: {
        ...prev.options,
        tooltip: { theme: mode }
      }
    }));
  }, [mode]);

  return (
    <MainCard content={false}>
      <Box sx={{ p: 3 }}>
        <Grid container direction="column" spacing={3} columns={12}>
          <Grid container spacing={1} sx={{ alignItems: 'center' }}>
            <Grid>
              <Typography variant="h3">Portfolio Value vs Collateral</Typography>
            </Grid>
          </Grid>
        </Grid>
      </Box>
      <Chart {...chartConfig} />
    </MainCard>
  );
}