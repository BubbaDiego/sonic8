// MonitorSummaryCard.jsx
import { useEffect } from 'react';
import { useTheme } from '@mui/material/styles';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import MainCard from 'ui-component/cards/MainCard';
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

  const blockSX = {
    p: 2.5,
    borderLeft: '1px solid ',
    borderBottom: '1px solid ',
    borderLeftColor: theme.palette.mode === ThemeMode.DARK ? 'dark.main' : 'grey.200',
    borderBottomColor: theme.palette.mode === ThemeMode.DARK ? 'dark.main' : 'grey.200',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    textAlign: 'center'
  };

  const iconSX = {
    width: 40,
    height: 40,
    color: 'secondary.main',
    borderRadius: '14px',
    p: 1,
    bgcolor: theme.palette.mode === ThemeMode.DARK ? 'background.default' : 'primary.light',
    marginBottom: 2
  };

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
    if (status === 'Healthy') return 'green';
    if (status === 'Warning') return 'yellow';
    return 'red';
  }

  return (
    <MainCard content={false}>
      <Grid container>
        {entries.map(([name, detail]) => {
          const Icon = iconMap[name] || IconShieldCheck;
          const color = statusColor(detail.status);
          const date =
            detail.last_updated && detail.last_updated !== 'Never'
              ? new Date(detail.last_updated)
              : null;
          return (
            <Grid
              key={name}
              className={`status-card monitor-style ${color}`}
              sx={blockSX}
              item
              xs={6}
            >
              <Icon stroke={1.5} style={iconSX} />
              <Typography className="label" variant="h5">
                {shortNameMap[name] || name}
              </Typography>
              <Typography className="value">
                <span className="monitor-time">
                  {date ? formatTime(date) : 'Never'}
                </span>
                {date && (
                  <span className="monitor-date"> {formatDate(date)}</span>
                )}
              </Typography>
              <Grid container spacing={1} justifyContent="center" alignItems="center" sx={{ mt: 1 }}>
                <span className={`led-dot ${color}`} />
                <Typography variant="subtitle2">
                  {detail.status}
                </Typography>
              </Grid>
            </Grid>
          );
        })}
      </Grid>
    </MainCard>
  );
}
