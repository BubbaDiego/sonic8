import { useEffect, useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import { useTheme } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Skeleton from '@mui/material/Skeleton';
import Chart from 'react-apexcharts';
import MainCard from 'ui-component/cards/MainCard';
import { useGetLatestPortfolio } from 'api/portfolio';

// ────────────────────────────────────────────────────────────

export default function CompositionPieCard({ maxHeight = 145, maxWidth = 190 }) {
  const theme = useTheme();
  const { portfolio, portfolioLoading } = useGetLatestPortfolio();

  // null = waiting • [] = no‑data • [long, short] = ready
  const [series, setSeries] = useState(null);

  // ─── Data pump ────────────────────────────────────────────
  useEffect(() => {
    if (portfolioLoading) return;

    const longSize  = Number(portfolio?.total_long_size  ?? 0);
    const shortSize = Number(portfolio?.total_short_size ?? 0);

    setSeries(longSize === 0 && shortSize === 0 ? [] : [longSize, shortSize]);
  }, [portfolio, portfolioLoading]);

  // ─── Derived chart props ─────────────────────────────────
  const { percentages, chartOptions } = useMemo(() => {
    if (!Array.isArray(series) || series.length !== 2) return {};

    const total = series[0] + series[1];
    const pct   = series.map(v => Math.round((v / total) * 100));

    return {
      percentages: pct,
      chartOptions: {
        labels: [`Long (${pct[0]}%)`, `Short (${pct[1]}%)`],
        colors: [theme.palette.success.main, theme.palette.error.main],
        legend: { show: false },
        tooltip: { theme: theme.palette.mode },
        dataLabels: {
          enabled: true,
          formatter: val => `${Math.round(val)}%`,
          style: { fontSize: '14px', fontWeight: 700, colors: ['#ffffff'] }
        },
        plotOptions: { pie: { dataLabels: { offset: -20 } } },
        noData: { text: 'No positions' }
      }
    };
  }, [series, theme]);

  // ─── Rendering branches ──────────────────────────────────
  if (series === null) {
    return (
      <MainCard sx={{ height: '100%', maxHeight, maxWidth, p: 2,
                      display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Skeleton variant="circular" width={120} height={120} />
      </MainCard>
    );
  }

  if (series.length === 0) {
    return (
      <MainCard sx={{ height: '100%', maxHeight, maxWidth, p: 2,
                      display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography variant="caption" color="text.secondary">
          No position data yet
        </Typography>
      </MainCard>
    );
  }

  // ─── Normal chart path ───────────────────────────────────
  return (
    <MainCard sx={{ height: '100%', maxHeight, maxWidth, p: 2,
                    display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Chart key={series.join('-')} options={chartOptions} series={series}
               type="pie" height={120} width={120} />
      </Box>
    </MainCard>
  );
}

// ────────────────────────────────────────────────────────────

CompositionPieCard.propTypes = {
  maxHeight: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  maxWidth:  PropTypes.oneOfType([PropTypes.string, PropTypes.number])
};
