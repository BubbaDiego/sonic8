import Grid from 'components/AppGrid';
import StatCard from './StatCard';
import MonetizationOnTwoToneIcon from '@mui/icons-material/MonetizationOnTwoTone';
import LocalFireDepartmentTwoToneIcon from '@mui/icons-material/LocalFireDepartmentTwoTone';
import TrendingUpTwoToneIcon from '@mui/icons-material/TrendingUpTwoTone';
import Inventory2TwoToneIcon from '@mui/icons-material/Inventory2TwoTone';

export default function PortfolioBar({ data = {}, variant = 'light', onToggle }) {
  const value = `$${Number(data.value || 0).toLocaleString()}`;
  const heat = Number(data.heatIndex || 0).toFixed(2);
  const leverage = Number(data.leverage || 0).toFixed(2);
  const size = `${(Number(data.size || 0) / 1000).toFixed(1)}k`;

  return (
    <Grid container spacing={2}>
      <Grid size={3}>
        <StatCard
          variant={variant}
          label="Value"
          value={value}
          icon={<MonetizationOnTwoToneIcon />}
          onClick={onToggle}
        />
      </Grid>
      <Grid size={3}>
        <StatCard
          variant={variant}
          label="Heat"
          value={heat}
          icon={<LocalFireDepartmentTwoToneIcon />}
          onClick={onToggle}
        />
      </Grid>
      <Grid size={3}>
        <StatCard
          variant={variant}
          label="Leverage"
          value={leverage}
          icon={<TrendingUpTwoToneIcon />}
          onClick={onToggle}
        />
      </Grid>
      <Grid size={3}>
        <StatCard
          variant={variant}
          label="Size"
          value={size}
          icon={<Inventory2TwoToneIcon />}
          onClick={onToggle}
        />
      </Grid>
    </Grid>
  );
}
