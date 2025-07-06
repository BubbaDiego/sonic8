// PerformanceGraphCard.jsx
import { useEffect, useState } from 'react';
import { alpha, useTheme } from '@mui/material/styles';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Chart from 'react-apexcharts';
import MainCard from 'ui-component/cards/MainCard';
import { ThemeMode } from 'config';
import useConfig from 'hooks/useConfig';
import chartData from './chart-data/market-share-area-chart';
import { IconCoin, IconPigMoney, IconChartAreaLine } from '@tabler/icons-react';

export default function PerformanceGraphCard() {
  const theme = useTheme();
  const { mode } = useConfig();
  const [chartConfig, setChartConfig] = useState(chartData);

  const secondaryMain = theme.palette.secondary.main;
  const errorMain = theme.palette.error.main;
  const primaryDark = theme.palette.primary.dark;

  useEffect(() => {
    setChartConfig((prevState) => ({
      ...prevState,
      options: {
        ...prevState.options,
        colors: [secondaryMain, primaryDark, errorMain],
        tooltip: { theme: mode }
      }
    }));
  }, [mode, theme.palette]);

  const iconSX = {
    width: 40,
    height: 40,
    color: 'secondary.main',
    borderRadius: '12px',
    padding: 1,
    bgcolor: mode === ThemeMode.DARK ? 'background.default' : 'primary.light'
  };

  return (
    <MainCard content={false}>
      <Box sx={{ p: 3 }}>
        <Grid container direction="column" spacing={3}>
          <Grid container spacing={1} alignItems="center">
            <Grid item>
              <Typography variant="h3">Performance Overview</Typography>
            </Grid>
          </Grid>
          <Grid item xs={12}>
            <Typography variant="h5" sx={{ mt: -2.5, fontWeight: 400 }}>
              Key Metrics Comparison
            </Typography>
          </Grid>
          <Grid container spacing={3} alignItems="center">
            <Grid item>
              <Grid container spacing={1} alignItems="center">
                <Grid item>
                  <Typography sx={iconSX}>
                    <IconCoin stroke={1.5} />
                  </Typography>
                </Grid>
                <Grid item xs>
                  <Typography variant="h4">Value</Typography>
                </Grid>
              </Grid>
            </Grid>
            <Grid item>
              <Grid container spacing={1} alignItems="center">
                <Grid item>
                  <Typography sx={iconSX}>
                    <IconPigMoney stroke={1.5} />
                  </Typography>
                </Grid>
                <Grid item xs>
                  <Typography variant="h4">Collateral</Typography>
                </Grid>
              </Grid>
            </Grid>
            <Grid item>
              <Grid container spacing={1} alignItems="center">
                <Grid item>
                  <Typography sx={iconSX}>
                    <IconChartAreaLine stroke={1.5} />
                  </Typography>
                </Grid>
                <Grid item xs>
                  <Typography variant="h4">SP500</Typography>
                </Grid>
              </Grid>
            </Grid>
          </Grid>
        </Grid>
      </Box>
      <Chart {...chartConfig} />
    </MainCard>
  );
}
