// src/components/OperationsBar.jsx
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { useTheme } from '@mui/material/styles';
import dayjs from 'dayjs';

import {
  IconShieldCheck,
  IconPlanet,
  IconSatellite,
  IconCurrencyDollar
} from '@tabler/icons-react';

import StatCard from './StatCard';

const iconMap = {
  'Sonic Monitoring': IconShieldCheck,
  'Price Monitoring': IconCurrencyDollar,
  'Positions Monitoring': IconPlanet,
  'XCom Communication': IconSatellite
};

function statusColor(theme, status) {
  if (status === 'Healthy') return theme.palette.success.main;
  if (status === 'Warning') return theme.palette.warning.main;
  return theme.palette.error.main;
}

export default function OperationsBar({ monitors = {}, variant = 'light', onToggle }) {
  const theme = useTheme();

  const getBackgroundColor = (ageMinutes) => {
    if (ageMinutes < 5) return theme.palette.primary.dark; // default blue
    if (ageMinutes < 10) return theme.palette.warning.main; // yellow
    return theme.palette.error.main; // red
  };

  return (
    <Stack
      direction="row"
      spacing={2}
      sx={{
        width: '100%',
        flexWrap: 'nowrap',
        alignItems: 'stretch'
      }}
    >
      {Object.entries(monitors).map(([name, detail]) => {
        const Icon = iconMap[name] ?? IconShieldCheck;

        const label = detail.last_updated
          ? dayjs(detail.last_updated).format('h:mm A')
          : '--';

        const color = statusColor(theme, detail.status);

        const ageMinutes = detail.last_updated
          ? dayjs().diff(dayjs(detail.last_updated), 'minute')
          : Number.POSITIVE_INFINITY;

        const cardBackground = getBackgroundColor(ageMinutes);

        return (
          <Box key={name} sx={{ flex: 1, minWidth: 0 }}>
            <StatCard
              variant="dark"
              icon={<Icon size={22} />}
              label={label}
              secondary={
                <Typography component="span" variant="caption" sx={{ color }}>
                  {detail.status}
                </Typography>
              }
              sx={{
                '& .MuiTypography-h4': { fontSize: '.775rem', textAlign: 'center' },
                '& .MuiTypography-subtitle2': { mt: 3 },
                backgroundColor: cardBackground,
                height: '100%',
                boxSizing: 'border-box'
              }}
              onClick={onToggle}
            />
          </Box>
        );
      })}
    </Stack>
  );
}
