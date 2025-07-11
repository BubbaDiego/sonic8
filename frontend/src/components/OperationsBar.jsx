import Grid from 'components/AppGrid';
import StatCard from './StatCard';
import { useTheme } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { IconShieldCheck, IconPlanet, IconSatellite, IconCurrencyDollar } from '@tabler/icons-react';

const iconMap = {
  'Sonic Monitoring': IconShieldCheck,
  'Price Monitoring': IconCurrencyDollar,
  'Positions Monitoring': IconPlanet,
  'XCom Communication': IconSatellite
};

const shortNameMap = {
  'Sonic Monitoring': 'Sonic',
  'Price Monitoring': 'Price',
  'Positions Monitoring': 'Positions',
  'XCom Communication': 'XCom'
};

function statusColor(theme, status) {
  if (status === 'Healthy') return theme.palette.success.main;
  if (status === 'Warning') return theme.palette.warning.main;
  return theme.palette.error.main;
}

export default function OperationsBar({ monitors = {}, variant = 'light', onToggle }) {
  const theme = useTheme();
  return (
    <Grid container spacing={2}>
      {Object.entries(monitors).map(([name, detail]) => {
        const Icon = iconMap[name];
        const color = statusColor(theme, detail.status);
        const value = (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
            {Icon && <Icon size={18} style={{ color }} />}
            <Typography variant="body2" sx={{ color }}>{detail.status}</Typography>
          </Box>
        );
        const short = shortNameMap[name] || name;
        const secondary = detail.last_updated ? new Date(detail.last_updated).toLocaleString() : 'Never';
        return (
          <Grid size={3} key={name}>
            <StatCard
              variant={variant}
              label={short}
              value={value}
              secondary={secondary}
              onClick={onToggle}
            />
          </Grid>
        );
      })}
    </Grid>
  );
}
