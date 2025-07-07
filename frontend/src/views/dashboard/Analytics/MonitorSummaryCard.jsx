
// MonitorSummaryCard.jsx
import { useEffect } from 'react';
import { useTheme } from '@mui/material/styles';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import MainCard from 'ui-component/cards/MainCard';
import Box from '@mui/material/Box';
import { ThemeMode } from 'config';
import { IconShieldCheck, IconPlanet, IconSatellite, IconCurrencyDollar } from '@tabler/icons-react';
import { useGetMonitorStatus, refreshMonitorStatus } from 'api/monitorStatus';

export default function MonitorSummaryCard() {
  const theme = useTheme();
  const { monitorStatus } = useGetMonitorStatus();

  useEffect(() => {
    const id = setInterval(() => refreshMonitorStatus(), 30000);
    return () => clearInterval(id);
  }, []);

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

  function formatTime(d) {
    let hours = d.getHours();
    const minutes = d.getMinutes().toString().padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours %= 12;
    if (hours === 0) hours = 12;
    return `${hours}:${minutes} ${ampm}`;
  }

  function formatDate(d) {
    const month = d.getMonth() + 1;
    const day = d.getDate();
    const year = d.getFullYear().toString().slice(-2);
    return `${month}/${day}/${year}`;
  }

  const entries = Object.entries(monitorStatus?.monitors || {});

  function statusColor(status) {
    if (status === 'Healthy') return theme.palette.success.main;
    if (status === 'Warning') return theme.palette.warning.main;
    return theme.palette.error.main;
  }

  return (
    <MainCard content={false}>
      <Box sx={{ p: 2 }}>
        <Grid container spacing={2}>
          {entries.map(([name, detail]) => {
            const Icon = iconMap[name] || IconShieldCheck;
            const color = statusColor(detail.status);
            const date =
              detail.last_updated && detail.last_updated !== 'Never'
                ? new Date(detail.last_updated)
                : null;

            return (
              <Grid key={name} item xs={6} sx={{ textAlign: 'center' }}>
                <Icon style={{ width: 40, height: 40, color }} />
                <Typography variant="subtitle1" fontWeight="bold" sx={{ mt: 1 }}>
                  {shortNameMap[name] || name}
                </Typography>
                <Typography variant="body2" sx={{ mt: 0.5 }}>
                  {date ? `${formatTime(date)} ${formatDate(date)}` : 'Never'}
                </Typography>
                <Typography variant="body2" sx={{ color, fontWeight: 'medium', mt: 0.5 }}>
                  {detail.status}
                </Typography>
              </Grid>
            );
          })}
        </Grid>
      </Box>
    </MainCard>
  );
}
