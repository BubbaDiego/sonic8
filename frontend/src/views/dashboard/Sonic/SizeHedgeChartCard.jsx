import { useEffect, useState } from 'react';

// material-ui
import { useTheme } from '@mui/material/styles';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';

// third party
import Chart from 'react-apexcharts';

// project imports
import useConfig from 'hooks/useConfig';
import { ThemeMode } from 'config';
import MainCard from 'ui-component/cards/MainCard';
import axios from 'utils/axios';

const initialChartData = {
  series: [0, 0],
  options: {
    chart: { type: 'pie', height: 350 },
    labels: ['Long', 'Short'],
    legend: {
      position: 'bottom'
    },
    responsive: [
      {
        breakpoint: 450,
        options: {
          chart: { height: 280 },
          legend: { position: 'bottom' }
        }
      }
    ]
  }
};

// ========================|| SIZE HEDGE PIE CHART CARD ||======================= //

export default function SizeHedgeChartCard() {
  const theme = useTheme();
  const { mode } = useConfig();
  const [chartConfig, setChartConfig] = useState(initialChartData);

  useEffect(() => {
    async function loadData() {
      try {
        const response = await axios.get('/positions');
        const data = response.data || [];
        const longSize = data.reduce(
          (sum, p) =>
            p.position_type && p.position_type.toLowerCase() === 'long'
              ? sum + parseFloat(p.size || 0)
              : sum,
          0
        );
        const shortSize = data.reduce(
          (sum, p) =>
            p.position_type && p.position_type.toLowerCase() === 'short'
              ? sum + parseFloat(p.size || 0)
              : sum,
          0
        );
        setChartConfig((prev) => ({ ...prev, series: [longSize, shortSize] }));
      } catch (e) {
        console.error(e);
      }
    }
    loadData();
  }, []);

  useEffect(() => {
    setChartConfig((prev) => ({
      ...prev,
      options: {
        ...prev.options,
        colors: [theme.palette.success.main, theme.palette.error.main],
        tooltip: { theme: mode }
      }
    }));
  }, [mode, theme.palette]);

  return (
    <MainCard content={false}>
      <Box sx={{ p: 3 }}>
        <Grid container direction="column" spacing={1}>
          <Grid item>
            <Typography variant="h3">Long vs Short Size</Typography>
          </Grid>
          <Grid item>
            <Typography sx={{ mt: -1, fontWeight: 400 }} color="inherit" variant="h5">
              Portfolio size breakdown
            </Typography>
          </Grid>
        </Grid>
      </Box>
      <Chart options={chartConfig.options} series={chartConfig.series} type="pie" height={chartConfig.options.chart.height} />
    </MainCard>
  );
}
