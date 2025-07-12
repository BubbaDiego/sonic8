import Grid from 'components/AppGrid';
import StatCard from './StatCard';
import { useTheme } from '@mui/material/styles';
import Typography from '@mui/material/Typography';
import dayjs from 'dayjs';
import {
  IconShieldCheck,
  IconPlanet,
  IconSatellite,
  IconCurrencyDollar
} from '@tabler/icons-react';

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
        const label = shortNameMap[name] || name;
        const time = detail.last_updated
          ? dayjs(detail.last_updated).format('h:mm A')
          : '--';
        const color = statusColor(theme, detail.status);

        return (
          <Grid size={3} key={name}>
            <StatCard
              variant={variant}
              icon={<Icon size={22} />}
              label={time} // switched to middle
              value={label} // moved to top
              secondary={
                <Typography component="span" variant="caption" sx={{ color }}>
                  {detail.status}
                </Typography>
              }
              onClick={onToggle}
            />
          </Grid>
        );
      })}
    </Grid>
  );
}
