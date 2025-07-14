import { useEffect, useState, useMemo } from 'react';
import { useTheme } from '@mui/material/styles';
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Chart from 'react-apexcharts';
import MainCard from 'ui-component/cards/MainCard';
import { ThemeMode } from 'config';
import useConfig from 'hooks/useConfig';
import { useGetPortfolioHistory } from 'api/portfolio';
import { IconCoin, IconPigMoney, IconChartAreaLine } from '@tabler/icons-react';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import ToggleButton from '@mui/material/ToggleButton';
import { startOfWeek, format, parseISO } from 'date-fns';

export default function PerformanceGraphCard() {
  const theme = useTheme();
  const { mode } = useConfig();
  const { history = [], historyLoading } = useGetPortfolioHistory();
  const [granularity, setGranularity] = useState('24');

  const bucketHistory = (granularity, rows = []) => {
    const buckets = new Map();

    rows.forEach((row) => {
      const date = parseISO(row.snapshot_time);
      let key;
      if (granularity === '1w') {
        key = format(startOfWeek(date), 'yyyy-MM-dd');
      } else if (granularity === '24') {
        key = format(date, 'yyyy-MM-dd');
      } else if (granularity === '12') {
        key = format(date, 'yyyy-MM-dd HH');
      } else {
        key = format(date, 'yyyy-MM-dd HH:mm');
      }

      const prev = buckets.get(key) ?? { value: 0, collateral: 0, btc: 0, count: 0 };
      buckets.set(key, {
        value: prev.value + Number(row.total_value || 0),
        collateral: prev.collateral + Number(row.total_collateral || 0),
        btc: prev.btc + Number(row.market_average_btc || 0),
        count: prev.count + 1
      });
    });

    const categories = [], valueSeries = [], collateralSeries = [], btcSeries = [];
    [...buckets.entries()].sort(([a], [b]) => a.localeCompare(b)).forEach(([k, v]) => {
      categories.push(k);
      valueSeries.push(Math.round(v.value / v.count));
      collateralSeries.push(Math.round(v.collateral / v.count));
      btcSeries.push(Math.round(v.btc / v.count));
    });

    return { categories, valueSeries, collateralSeries, btcSeries };
  };

  const bucketed = useMemo(() => bucketHistory(granularity, history), [granularity, history]);

  const [chartConfig, setChartConfig] = useState({
    series: [],
    options: {
      chart: {
        animations: { enabled: false },
        zoom: { enabled: true, autoScaleYaxis: true },
        toolbar: { show: true, tools: { download: false }, autoSelected: 'zoom' }
      },
      stroke: { curve: 'smooth', width: 2 },
      dataLabels: { enabled: false },
      markers: { size: 0 },
      yaxis: { forceNiceScale: true },
      xaxis: { categories: [] },
      tooltip: { theme: mode }
    }
  });

  useEffect(() => {
    if (historyLoading) return;

    const { categories, valueSeries, collateralSeries, btcSeries } = bucketed;

    setChartConfig((prevState) => ({
      ...prevState,
      series: [
        { name: 'Value', data: valueSeries, color: theme.palette.primary.main },
        { name: 'Collateral', data: collateralSeries, color: theme.palette.secondary.main },
        { name: 'BTC', data: btcSeries }
      ],
      options: { ...prevState.options, xaxis: { categories }, tooltip: { theme: mode } }
    }));
  }, [bucketed, historyLoading, mode, theme.palette.primary.main, theme.palette.secondary.main]);

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
        <Grid container spacing={2} alignItems="center" justifyContent="space-between">
          <Grid item>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box sx={iconSX}><IconCoin stroke={1.5} /></Box>
              <Box component="span" sx={{ typography: 'subtitle1', color: theme.palette.primary.main }}>{bucketed.valueSeries.at(-1)}</Box>
              <Box sx={iconSX}><IconPigMoney stroke={1.5} /></Box>
              <Box component="span" sx={{ typography: 'subtitle1', color: theme.palette.secondary.main }}>{bucketed.collateralSeries.at(-1)}</Box>
              <Box sx={iconSX}><IconChartAreaLine stroke={1.5} /></Box>
              <Box component="span" sx={{ typography: 'subtitle1' }}>BTC</Box>
            </Box>
          </Grid>
          <Grid item>
            <ToggleButtonGroup size="small" exclusive value={granularity} onChange={(_, v) => v && setGranularity(v)}>
              <ToggleButton value="1">1hr</ToggleButton>
              <ToggleButton value="12">12hr</ToggleButton>
              <ToggleButton value="24">24hr</ToggleButton>
              <ToggleButton value="1w">1w</ToggleButton>
            </ToggleButtonGroup>
          </Grid>
        </Grid>
      </Box>
      <Box sx={{ flexGrow: 1, minHeight: 220, px: 1 }}>
        <Chart {...chartConfig} height="100%" />
      </Box>
    </MainCard>
  );
}