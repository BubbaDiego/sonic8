import React, { useMemo } from 'react';
import { Card, CardHeader, CardContent, Typography, Stack, Box, Button } from '@mui/material';
import ShowChartTwoToneIcon from '@mui/icons-material/ShowChartTwoTone';
import MarketMovementCard from '../../components/MarketMovementCard';
import MonitorUpdateBar    from '../../components/MonitorUpdateBar';

export default function MarketMonitorCard({ cfg, setCfg, live = {}, disabled = false }) {
  const normCfg = useMemo(
    () => ({
      notifications: {
        system: true,
        voice: true,
        sms: false,
        tts: true,
        ...(cfg.notifications || {})
      },
      ...cfg
    }),
    [cfg]
  );

  const toggleNotification = (key) => {
    setCfg(prev => ({
      ...prev,
      notifications: { ...prev.notifications, [key]: !prev.notifications[key] }
    }));
  };

  return (
    <Card variant="outlined" sx={{ display: 'flex', flexDirection: 'column', height: '100%', opacity: disabled ? 0.4 : 1 }}>
      <CardHeader
        title={
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h4" fontWeight={700} sx={{ fontSize: '1.6rem' }}>
              Market Monitor
            </Typography>
            <ShowChartTwoToneIcon fontSize="medium" />
          </Stack>
        }
      />
      <CardContent sx={{ p: 0 }}>
        <MarketMovementCard cfg={cfg} setCfg={setCfg} live={live} />
      </CardContent>

      <Box sx={{ flexGrow: 1 }} />

      <MonitorUpdateBar
        cfg={normCfg.notifications}
        toggle={toggleNotification}
        sx={{ mx: 2, mb: 2 }}
      />
    </Card>
  );
}
