// MonitorSummaryCard.jsx
import { useEffect } from 'react';
import { useTheme } from '@mui/material/styles';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import MainCard from 'ui-component/cards/MainCard';
import Box from '@mui/material/Box';
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

  function statusColor(status) {
    if (status === 'Healthy') return theme.palette.success.main;
    if (status === 'Warning') return theme.palette.warning.main;
    return theme.palette.error.main;
  }

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
    return `${month}/${day}`;
  }

  return (
    <MainCard content={false}>
      <Box sx={{ p: 2 }}>
        <Grid container spacing={2}>
          {Object.entries(monitorStatus?.monitors || {}).map(([name, detail]) => {
            const Icon = iconMap[name];
            const color = statusColor(detail.status);
            const date = detail.last_updated ? new Date(detail.last_updated) : null;

            return (
              <Grid key={name} item xs={6} sx={{ textAlign: 'center' }}>
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mb: 0.5 }}>
                  <Icon stroke={1.5} style={{ width: 35, height: 35, color }} />
                </Box>
                <Typography variant="subtitle2" fontWeight="bold" sx={{ fontSize: '0.8rem', mb: 0.25, color: 'white' }}>
                  {shortNameMap[name]}
                </Typography>
                <Typography variant="caption" sx={{ fontSize: '0.7rem', display: 'block', fontWeight: 'bold' }}>
                  {date ? `${formatTime(date)} ${formatDate(date)}` : 'Never'}
                </Typography>
                <Typography variant="caption" sx={{ color, fontWeight: 'medium', fontSize: '0.7rem', display: 'block', mt: 0.25 }}>
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
