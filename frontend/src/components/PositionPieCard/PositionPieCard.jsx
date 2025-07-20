import { useMemo } from 'react';
import PropTypes from 'prop-types';
import { useTheme } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Skeleton from '@mui/material/Skeleton';
import Typography from '@mui/material/Typography';
import Chart from 'react-apexcharts';
import MainCard from 'ui-component/cards/MainCard';
import { useGetPositions } from 'api/positions';

/* helper: returns a long rotating palette */
const palette = (t) => [
  t.palette.primary.main,
  t.palette.success.main,
  t.palette.error.main,
  t.palette.warning.main,
  t.palette.info.main,
  t.palette.secondary.main,
  t.palette.primary.light,
  t.palette.success.light,
  t.palette.error.light,
  t.palette.warning.light,
  t.palette.info.light,
  t.palette.secondary.light,
  '#26C6DA',
  '#7E57C2',
  '#EC407A',
  '#FF7043'
];

export default function PositionPieCard({ maxHeight = 260, maxWidth = 320 }) {
  const theme = useTheme();
  const { positions, positionsLoading } = useGetPositions();

  /* —— crunch data —— */
  const { series, labels, colors, opts } = useMemo(() => {
    if (positionsLoading || !Array.isArray(positions)) return {};

    const colours = palette(theme);

    const mapped = positions
      .filter((p) => Number(p.value))
      .map((p, i) => ({
        name:  p.asset_type || `#${i + 1}`,
        size:  Math.abs(Number(p.value)),
        color: colours[i % colours.length]
      }));

    if (!mapped.length) return { series: [] };

    return {
      series: mapped.map((m) => m.size),
      labels: mapped.map((m) => m.name),
      colors: mapped.map((m) => m.color),
      opts: {
        chart:   { type: 'pie', animations: { speed: 200 } },
        labels:  mapped.map((m) => m.name),
        colors:  mapped.map((m) => m.color),
        legend:  { show: false },           // hide legend → more space
        tooltip: { theme: theme.palette.mode },
        dataLabels: {
          enabled: true,
          style: { fontSize: '11px', fontWeight: 600, colors: ['#fff'] },
          formatter: (v) => `${v.toFixed(1)}%`
        },
        stroke: { colors: ['transparent'] },
        noData: { text: 'No positions' }
      }
    };
  }, [positions, positionsLoading, theme]);

  /* —— branches —— */
  if (positionsLoading) {
    return (
      <MainCard sx={{ height: '100%', maxHeight, maxWidth, p: 2,
                      display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Skeleton variant="circular" width={180} height={180} />
      </MainCard>
    );
  }

  if (!series || series.length === 0) {
    return (
      <MainCard sx={{ height: '100%', maxHeight, maxWidth, p: 2,
                      display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography variant="caption" color="text.secondary">
          No open positions
        </Typography>
      </MainCard>
    );
  }

  /* —— chart —— */
  return (
    <MainCard sx={{ height: '100%', maxHeight, maxWidth, p: 1 }}>
      {/* full‑width box so the pie fills the card */}
      <Box sx={{ width: '100%', height: 220, display: 'flex', justifyContent: 'center' }}>
        <Chart options={opts} series={series} type="pie" width="100%" height="100%" />
      </Box>
    </MainCard>
  );
}

PositionPieCard.propTypes = {
  maxHeight: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  maxWidth:  PropTypes.oneOfType([PropTypes.number, PropTypes.string])
};
