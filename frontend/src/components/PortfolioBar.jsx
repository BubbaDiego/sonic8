import Grid from 'components/AppGrid';
import StatCard from './StatCard';

export default function PortfolioBar({ data = {}, variant = 'light' }) {
  const value = `$${Number(data.value || 0).toLocaleString()}`;
  const heat = Number(data.heatIndex || 0).toFixed(2);
  const leverage = Number(data.leverage || 0).toFixed(2);
  const size = `${(Number(data.size || 0) / 1000).toFixed(1)}k`;

  return (
    <Grid container spacing={2}>
      <Grid size={3}>
        <StatCard variant={variant} label="Value" value={value} />
      </Grid>
      <Grid size={3}>
        <StatCard variant={variant} label="Heat" value={heat} />
      </Grid>
      <Grid size={3}>
        <StatCard variant={variant} label="Leverage" value={leverage} />
      </Grid>
      <Grid size={3}>
        <StatCard variant={variant} label="Size" value={size} />
      </Grid>
    </Grid>
  );
}
