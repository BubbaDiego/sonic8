// CompositionPieCard.jsx
import { useEffect, useState } from 'react';
import { useTheme } from '@mui/material/styles';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Chart from 'react-apexcharts';
import MainCard from 'ui-component/cards/MainCard';
import { useGetPositions } from 'api/positions';

export default function CompositionPieCard() {
  const theme = useTheme();
  const { positions = [], positionsLoading } = useGetPositions();

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
    if (positionsLoading || !positions.length) return;

    const longSize = positions
      .filter(pos => pos.side === 'long')
      .reduce((sum, pos) => sum + pos.size, 0);

    const shortSize = positions
      .filter(pos => pos.side === 'short')
      .reduce((sum, pos) => sum + pos.size, 0);

    setSeries([longSize, shortSize]);
  }, [positions, positionsLoading]);

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
