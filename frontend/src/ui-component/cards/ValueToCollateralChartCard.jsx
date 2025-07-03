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
import axios from 'utils/axios';

// canned data for initial UI
const initialChartData = {
  series: [
    { name: 'Total Value', data: [0] },
    { name: 'Total Collateral', data: [0] }
  ],
  options: {
    chart: { type: 'area', height: 350 },
    colors: ['#4caf50', '#ff9800'],
    dataLabels: { enabled: false },
    stroke: { curve: 'smooth' },
    xaxis: { categories: ['Totals'] },
    tooltip: { theme: 'light' }
  }
};

// ===========================|| VALUE TO COLLATERAL CHART CARD ||=========================== //

export default function ValueToCollateralChartCard() {
  const theme = useTheme();
  const { mode } = useConfig();
  const [chartConfig, setChartConfig] = useState(initialChartData);

  useEffect(() => {
    async function loadData() {
      try {
        const response = await axios.get('/positions');
        const data = response.data || [];
        const totalValue = data.reduce((sum, p) => sum + parseFloat(p.value || 0), 0);
        const totalCollateral = data.reduce(
          (sum, p) => sum + parseFloat(p.collateral || 0),
          0
        );
        setChartConfig((prev) => ({
          ...prev,
          series: [
            { name: 'Total Value', data: [totalValue] },
            { name: 'Total Collateral', data: [totalCollateral] }
          ]
        }));
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
        tooltip: { theme: mode }
      }
    }));
  }, [mode]);

  return (
    <MainCard content={false}>
      <Box sx={{ p: 3 }}>
        <Grid container direction="column" spacing={3}>
          <Grid container spacing={1} sx={{ alignItems: 'center' }}>
            <Grid>
              <Typography variant="h3">Portfolio Value vs Collateral</Typography>
            </Grid>
          </Grid>
          <Grid item xs={12}>
            <Typography sx={{ mt: -1, fontWeight: 400 }} color="inherit" variant="h5">
              Weekly comparison of portfolio metrics
            </Typography>
          </Grid>
        </Grid>
      </Box>
      <Chart {...chartConfig} />
    </MainCard>
  );
}