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
import {
  startOfWeek,
  format,
  parseISO,
  subHours,
  subDays
} from 'date-fns';

/* ────────────────────────────────────────────────────────────────────────── */
/* Helpers                                                                   */
/* ────────────────────────────────────────────────────────────────────────── */
const fmt = (n, d = 0) =>
  n?.toLocaleString(undefined, { maximumFractionDigits: d });

const calcPerf = (series) => {
  if (!series || series.length < 1) return { delta: 0, pct: 0 };
  const first = series[0];
  const last = series.at(-1);
  const delta = last - first;
  return {
    delta,
    pct: first ? (delta / first) * 100 : 0
  };
};

export default function PerformanceGraphCard() {
  const theme = useTheme();
  const { mode } = useConfig();
  const { history = [], historyLoading } = useGetPortfolioHistory();

  // 1 = 1 hr • 12 = 12 hr • 24 = 24 hr • 1w = 7 days
  const [granularity, setGranularity] = useState('24');

  /* ──────────────────────────────────────────────────────────────────────── */
  /* History bucketing with a rolling window that matches the granularity   */
  /* ──────────────────────────────────────────────────────────────────────── */
  const bucketHistory = (gran, rows = []) => {
    if (!rows.length)
      return {
        categories: [],
        valueSeries: [],
        collateralSeries: [],
        btcSeries: []
      };

    const now = parseISO(rows.at(-1).snapshot_time);
    const windowStart =
      gran === '1'
        ? subHours(now, 1)
        : gran === '12'
        ? subHours(now, 12)
        : gran === '24'
        ? subDays(now, 1)
        : subDays(now, 7); // 1 w

    const buckets = new Map();

    rows.forEach((row) => {
      const date = parseISO(row.snapshot_time);
      if (date < windowStart) return; // ignore data outside active window

      let key;
      if (gran === '1w') {
        key = format(startOfWeek(date), 'yyyy-MM-dd');
      } else if (gran === '24') {
        key = format(date, 'yyyy-MM-dd');
      } else if (gran === '12') {
        key = format(date, 'yyyy-MM-dd HH');
      } else {
        key = format(date, 'yyyy-MM-dd HH:mm');
      }

      const prev = buckets.get(key) ?? {
        value: 0,
        collateral: 0,
        btc: 0,
        count: 0
      };

      buckets.set(key, {
        value: prev.value + Number(row.total_value || 0),
        collateral: prev.collateral + Number(row.total_collateral || 0),
        btc: prev.btc + Number(row.market_average_btc || 0),
        count: prev.count + 1
      });
    });

    const categories = [],
      valueSeries = [],
      collateralSeries = [],
      btcSeries = [];

    [...buckets.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .forEach(([k, v]) => {
        categories.push(k);
        valueSeries.push(Math.round(v.value / v.count));
        collateralSeries.push(Math.round(v.collateral / v.count));
        btcSeries.push(Math.round(v.btc / v.count));
      });

    return { categories, valueSeries, collateralSeries, btcSeries };
  };

  const bucketed = useMemo(
    () => bucketHistory(granularity, history),
    [granularity, history]
  );

  /* ──────────────────────────────────────────────────────────────────────── */
  /* Chart config                                                            */
  /* ──────────────────────────────────────────────────────────────────────── */
  const [chartConfig, setChartConfig] = useState({
    series: [],
    options: {
      chart: {
        type: 'area', // ⇠ area chart so we get the fill
        animations: { enabled: false },
        zoom: { enabled: true, autoScaleYaxis: true },
        toolbar: { show: true, tools: { download: false }, autoSelected: 'zoom' }
      },
      stroke: { curve: 'smooth', width: 4 }, // thicker line (4 px)
      fill: {
        type: 'gradient',
        gradient: {
          shadeIntensity: 1,
          opacityFrom: 0.3, // stronger at top
          opacityTo: 0.05,  // fades out
          stops: [0, 90, 100]
        }
      },
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

    setChartConfig((prev) => ({
      ...prev,
      series: [
        { name: 'Value', data: valueSeries, color: theme.palette.primary.main },
        {
          name: 'Collateral',
          data: collateralSeries,
          color: theme.palette.secondary.main
        },
        { name: 'BTC', data: btcSeries, color: theme.palette.info.main }
      ],
      options: {
        ...prev.options,
        xaxis: { categories },
        tooltip: { theme: mode }
      }
    }));
  }, [
    bucketed,
    historyLoading,
    mode,
    theme.palette.primary.main,
    theme.palette.secondary.main,
    theme.palette.info.main
  ]);

  /* ──────────────────────────────────────────────────────────────────────── */
  /*  Performance deltas                                                     */
  /* ──────────────────────────────────────────────────────────────────────── */
  const valuePerf = calcPerf(bucketed.valueSeries);
  const collateralPerf = calcPerf(bucketed.collateralSeries);
  const btcPerf = calcPerf(bucketed.btcSeries);

  const perfColour = (delta) => (delta >= 0 ? 'success.main' : 'error.main');

  const PerfChip = ({ delta, pct }) => (
    <Box
      component="span"
      sx={{
        typography: 'caption',
        color: perfColour(delta),
        ml: 0.5 // small gap after the base value
      }}
    >
      {delta >= 0 ? '+' : ''}
      {fmt(delta)} ({fmt(pct, 1)}%)
    </Box>
  );

  const iconSX = {
    width: 30,
    height: 30,
    color: 'secondary.main',
    borderRadius: '12px',
    p: 0.5,
    bgcolor: mode === ThemeMode.DARK ? 'background.default' : 'primary.light'
  };

  /* ──────────────────────────────────────────────────────────────────────── */
  /* Render                                                                  */
  /* ──────────────────────────────────────────────────────────────────────── */
  return (
    <MainCard
      content={false}
      sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}
    >
      {/* Header row */}
      <Box sx={{ p: 1.5, flexShrink: 0 }}>
        <Grid
          container
          spacing={2}
          alignItems="center"
          justifyContent="space-between"
        >
          {/* Metrics */}
          <Grid item>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {/* Value */}
              <Box sx={iconSX}>
                <IconCoin stroke={1.5} />
              </Box>
              <Box
                component="span"
                sx={{
                  typography: 'subtitle1',
                  color: theme.palette.primary.main
                }}
              >
                {fmt(bucketed.valueSeries.at(-1))}
              </Box>
              <PerfChip {...valuePerf} />

              {/* Collateral */}
              <Box sx={iconSX}>
                <IconPigMoney stroke={1.5} />
              </Box>
              <Box
                component="span"
                sx={{
                  typography: 'subtitle1',
                  color: theme.palette.secondary.main
                }}
              >
                {fmt(bucketed.collateralSeries.at(-1))}
              </Box>
              <PerfChip {...collateralPerf} />

              {/* BTC */}
              <Box sx={iconSX}>
                <IconChartAreaLine stroke={1.5} />
              </Box>
              <Box
                component="span"
                sx={{ typography: 'subtitle1', color: theme.palette.info.main }}
              >
                {fmt(bucketed.btcSeries.at(-1))}
              </Box>
              <PerfChip {...btcPerf} />
            </Box>
          </Grid>

          {/* Toggle */}
          <Grid item>
            <ToggleButtonGroup
              size="small"
              exclusive
              value={granularity}
              onChange={(_, v) => v && setGranularity(v)}
            >
              <ToggleButton value="1">1hr</ToggleButton>
              <ToggleButton value="12">12hr</ToggleButton>
              <ToggleButton value="24">24hr</ToggleButton>
              <ToggleButton value="1w">1w</ToggleButton>
            </ToggleButtonGroup>
          </Grid>
        </Grid>
      </Box>

      {/* Chart */}
      <Box sx={{ flexGrow: 1, minHeight: 220, px: 1 }}>
        <Chart {...chartConfig} height="100%" />
      </Box>
    </MainCard>
  );
}
