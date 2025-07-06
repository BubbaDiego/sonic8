import { useEffect } from 'react';
import { useTheme } from '@mui/material/styles';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import MainCard from 'ui-component/cards/MainCard';
import { ThemeMode } from 'config';
import { IconShare, IconAccessPoint, IconCircles, IconCreditCard } from '@tabler/icons-react';

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
    borderBottomColor: theme.palette.mode === ThemeMode.DARK ? 'dark.main' : 'grey.200'
  };

  const iconMap = {
    'Sonic Monitoring': IconShare,
    'Price Monitoring': IconAccessPoint,
    'Positions Monitoring': IconCircles,
    'XCom Communication': IconCreditCard
  };

  const entries = Object.entries(monitorStatus?.monitors || {});
  const rows = [];
  for (let i = 0; i < entries.length; i += 2) {
    rows.push(entries.slice(i, i + 2));
  }

  function statusColor(status) {
    if (status === 'Healthy') return 'green';
    if (status === 'Warning') return 'yellow';
    return 'red';
  }

  return (
    <MainCard
      content={false}
      sx={{
        '& svg': {
          width: 50,
          height: 50,
          color: 'secondary.main',
          borderRadius: '14px',
          p: 1.25,
          bgcolor: theme.palette.mode === ThemeMode.DARK ? 'background.default' : 'primary.light'
        }
      }}
    >
      {rows.map((row, idx) => (
        <Grid key={idx} container spacing={0} sx={{ alignItems: 'center' }}>
          {row.map(([name, detail]) => {
            const Icon = iconMap[name] || IconShare;
            const color = statusColor(detail.status);
            const date = detail.last_updated ? new Date(detail.last_updated) : null;
            return (
              <Grid key={name} className={`status-card monitor-style ${color}`} sx={blockSX} size={{ xs: 12, sm: 6 }}>
                <Grid container spacing={1} sx={{ alignItems: 'center', justifyContent: { xs: 'space-between', sm: 'center' } }}>
                  <Grid className="icon">
                    <Icon stroke={1.5} />
                  </Grid>
                  <Grid size={{ sm: 'grow' }}>
                    <Typography className="label" align="center">
                      {name}
                    </Typography>
                    <Typography className="value" align="center">
                      <span className="monitor-time">{date ? date.toLocaleTimeString() : 'Never'}</span>
                      {date && <span className="monitor-date">{date.toLocaleDateString()}</span>}
                    </Typography>
                    <Grid container spacing={1} justifyContent="center" sx={{ mt: 0.5, flexWrap: 'nowrap' }}>
                      <span className={`led-dot ${color}`} />
                      <Typography variant="subtitle2" align="center">
                        {detail.status}
                      </Typography>
                    </Grid>
                  </Grid>
                </Grid>
              </Grid>
            );
          })
        </Grid>
      ))
    </MainCard>
  );
}
