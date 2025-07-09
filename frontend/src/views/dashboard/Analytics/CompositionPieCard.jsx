// CompositionPieCard.jsx
import { useEffect, useState } from 'react';
import { useTheme } from '@mui/material/styles';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Chart from 'react-apexcharts';
import MainCard from 'ui-component/cards/MainCard';
import { useGetLatestPortfolio } from 'api/portfolio';

export default function CompositionPieCard() {
  const theme = useTheme();
  const { portfolio, portfolioLoading } = useGetLatestPortfolio();

  const [series, setSeries] = useState([0, 0]);
  const chartOptions = {
    labels: ['Long Positions', 'Short Positions'],
    colors: [theme.palette.success.main, theme.palette.error.main],
    legend: {
      show: true,
      position: 'bottom'
    },
    tooltip: {
      theme: 'dark'
    }
  };

  useEffect(() => {
    if (portfolioLoading || !portfolio) return;

    const longSize = parseFloat(portfolio.total_long_size || 0);
    const shortSize = parseFloat(portfolio.total_short_size || 0);

    setSeries([longSize, shortSize]);
  }, [portfolio, portfolioLoading]);

  return (
    <MainCard>
      <Box sx={{ p: 3 }}>
        <Grid container direction="column" spacing={2} alignItems="center">
          <Grid item>
            <Typography variant="h3">Positions Composition</Typography>
          </Grid>
          <Grid item xs={12} sx={{ width: '100%' }}>
            <Chart options={chartOptions} series={series} type="pie" height={250} />
          </Grid>
        </Grid>
      </Box>
    </MainCard>
  );
}
