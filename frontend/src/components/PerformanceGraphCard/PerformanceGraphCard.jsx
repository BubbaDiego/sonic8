import { useEffect, useState, useMemo } from 'react';
import { useTheme } from '@mui/material/styles';
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Chart from 'react-apexcharts';
import MainCard from 'ui-component/cards/MainCard';
import { ThemeMode } from 'config';
import useConfig from 'hooks/useConfig';
import { useGetPortfolioHistory } from 'api/portfolio';
import { useGetPriceHistory } from 'api/prices';

// Corrected and confirmed imports
import {
  IconCoin,
  IconPigMoney,
  IconCurrencyBitcoin,
  IconCurrencyEthereum,
  IconCurrencySolana
} from '@tabler/icons-react';

import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import ToggleButton from '@mui/material/ToggleButton';
import { startOfWeek, format, parseISO } from 'date-fns';

export default function PerformanceGraphCard() {
  const theme = useTheme();
  const { mode } = useConfig();

  const { history = [], historyLoading } = useGetPortfolioHistory();
  const [granularity, setGranularity] = useState('24');

  const [asset, setAsset] = useState('BTC');
  const cycleAsset = () =>
    setAsset((prev) => (prev === 'BTC' ? 'ETH' : prev === 'ETH' ? 'SOL' : 'BTC'));

  const bucketHistory = (gran, rows = []) => {
    const buckets = new Map();

    rows.forEach((row) => {
      const date = parseISO(row.snapshot_time || row.last_update_time);
      let key;
      if (gran === '1w') key = format(startOfWeek(date), 'yyyy-MM-dd');
      else if (gran === '24') key = format(date, 'yyyy-MM-dd');
      else if (gran === '12') key = format(date, 'yyyy-MM-dd HH');
      else key = format(date, 'yyyy-MM-dd HH:mm');

      const prev = buckets.get(key) ?? {
        value: 0,
        collateral: 0,
        price: 0,
        count: 0
      };

      buckets.set(key, {
        value: prev.value + Number(row.total_value || 0),
        collateral: prev.collateral + Number(row.total_collateral || 0),
        price: prev.price + Number(row.current_price || row.price || 0),
        count: prev.count + 1
      });
    });

    const categories = [], valueSeries = [], collateralSeries = [], priceSeries = [];

    [...buckets.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .forEach(([k, v]) => {
        categories.push(k);
        valueSeries.push(Math.round(v.value / v.count));
        collateralSeries.push(Math.round(v.collateral / v.count));
        priceSeries.push(Math.round(v.price / v.count));
      });

    return { categories, valueSeries, collateralSeries, priceSeries };
  };

  const bucketedPortfolio = useMemo(() => bucketHistory(granularity, history), [granularity, history]);

  const { history: priceHistory = [], historyLoading: priceLoading } = useGetPriceHistory(asset, granularity);
  const bucketedPrice = useMemo(() => bucketHistory(granularity, priceHistory), [granularity, priceHistory]);

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
    if (historyLoading || priceLoading) return;

    setChartConfig((prev) => ({
      ...prev,
      series: [
        { name: `${bucketedPortfolio.valueSeries.at(-1)}`, data: bucketedPortfolio.valueSeries, color: theme.palette.primary.main },
        { name: `${bucketedPortfolio.collateralSeries.at(-1)}`, data: bucketedPortfolio.collateralSeries, color: theme.palette.secondary.main },
        { name: asset, data: bucketedPrice.priceSeries }
      ],
      options: { ...prev.options, xaxis: { categories: bucketedPortfolio.categories }, tooltip: { theme: mode } }
    }));
  }, [bucketedPortfolio, bucketedPrice, historyLoading, priceLoading, asset, mode, theme.palette.primary.main, theme.palette.secondary.main]);

  const iconSX = {
    width: 30,
    height: 30,
    color: 'secondary.main',
    borderRadius: '12px',
    p: 0.5,
    bgcolor: mode === ThemeMode.DARK ? 'background.default' : 'primary.light'
  };

  return (
    <MainCard content={false} sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ p: 1.5, flexShrink: 0 }}>
        <Grid container spacing={2} alignItems="center" justifyContent="space-between">
          <Grid item>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box sx={iconSX}><IconCoin stroke={1.5} /></Box>
              <Box component="span" sx={{ typography: 'subtitle1', color: theme.palette.primary.main }}>{bucketedPortfolio.valueSeries.at(-1)}</Box>
              <Box sx={iconSX}><IconPigMoney stroke={1.5} /></Box>
              <Box component="span" sx={{ typography: 'subtitle1', color: theme.palette.secondary.main }}>{bucketedPortfolio.collateralSeries.at(-1)}</Box>
              <Box sx={{ ...iconSX, cursor: 'pointer' }} onClick={cycleAsset}>{ {BTC: <IconCurrencyBitcoin stroke={1.5}/>, ETH: <IconCurrencyEthereum stroke={1.5}/>, SOL: <IconCurrencySolana stroke={1.5}/>}[asset] }</Box>
              <Box component="span" sx={{ typography: 'subtitle1' }}>{asset}</Box>
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
