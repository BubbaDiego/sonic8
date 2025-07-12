import { useEffect, useState } from 'react';
import { useTheme } from '@mui/material/styles';
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Chart from 'react-apexcharts';
import MainCard from 'ui-component/cards/MainCard';
import { ThemeMode } from 'config';
import useConfig from 'hooks/useConfig';
import chartData from './chart-data/market-share-area-chart';
import { useGetPortfolioHistory } from 'api/portfolio';
import { IconCoin, IconPigMoney, IconChartAreaLine } from '@tabler/icons-react';

export default function PerformanceGraphCard() {
  const theme = useTheme();
  const { mode } = useConfig();
  const [chartConfig, setChartConfig] = useState({
    ...chartData,
    options: {
      ...chartData.options,
      chart: {
        ...chartData.options.chart,
        animations: { enabled: false },
        zoom: { enabled: false },
        toolbar: { show: false }
      },
      stroke: { curve: 'smooth', width: 2 },
      dataLabels: { enabled: false },
      markers: { size: 0 },
      yaxis: { forceNiceScale: true }
    }
  });

  const { history = [], historyLoading } = useGetPortfolioHistory();

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

  useEffect(() => {
    if (historyLoading) return;

    const categories = history.map((d) =>
      new Date(d.snapshot_time).toLocaleDateString()
    );
    const valueSeries = history.map((d) =>
      Math.round(parseFloat(d.total_value || 0))
    );
    const collateralSeries = history.map((d) =>
      Math.round(parseFloat(d.total_collateral || 0))
    );
    const sp500Series = history.map((d) =>
      Math.round(parseFloat(d.market_average_sp500 || 0))
    );

    setChartConfig((prevState) => ({
      ...prevState,
      series: [
        { name: 'Value', data: valueSeries },
        { name: 'Collateral', data: collateralSeries },
        { name: 'SP500', data: sp500Series }
      ],
      options: {
        ...prevState.options,
        xaxis: { ...prevState.options.xaxis, categories }
      }
    }));
  }, [history, historyLoading]);

  const iconSX = {
    width: 30,
    height: 30,
    color: 'secondary.main',
    borderRadius: '12px',
    padding: 0.5,
    bgcolor: mode === ThemeMode.DARK ? 'background.default' : 'primary.light'
  };

  return (
    <MainCard content={false} sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ p: 1.5, flexShrink: 0 }}>
        <Grid container spacing={2} alignItems="center" justifyContent="center">
          <Grid item>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box sx={iconSX}><IconCoin stroke={1.5} /></Box>
              <Box component="span" sx={{ typography: 'subtitle1' }}>Value</Box>
            </Box>
          </Grid>
          <Grid item>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box sx={iconSX}><IconPigMoney stroke={1.5} /></Box>
              <Box component="span" sx={{ typography: 'subtitle1' }}>Collateral</Box>
            </Box>
          </Grid>
          <Grid item>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box sx={iconSX}><IconChartAreaLine stroke={1.5} /></Box>
              <Box component="span" sx={{ typography: 'subtitle1' }}>SP500</Box>
            </Box>
          </Grid>
        </Grid>
      </Box>

      <Box sx={{ flexGrow: 1, minHeight: 220, px: 1 }}>
        <Chart {...chartConfig} height="100%" />
      </Box>
    </MainCard>
  );
}
