import React, { useMemo } from 'react';
import { Card, CardHeader, CardContent, Typography, Stack, Box, Button } from '@mui/material';
import ShowChartTwoToneIcon from '@mui/icons-material/ShowChartTwoTone';
import MemoryIcon from '@mui/icons-material/Memory';
import RecordVoiceOverIcon from '@mui/icons-material/RecordVoiceOver';
import SmsIcon from '@mui/icons-material/Sms';
import CampaignIcon from '@mui/icons-material/Campaign';

import MarketMovementCard from '../../components/MarketMovementCard';

function NotificationBar({ cfg, toggle }) {
  const items = [
    { key: 'system', label: 'System', icon: MemoryIcon, color: 'info' },
    { key: 'voice', label: 'Voice', icon: RecordVoiceOverIcon, color: 'success' },
    { key: 'sms', label: 'SMS', icon: SmsIcon, color: 'warning' },
    { key: 'tts', label: 'TTS', icon: CampaignIcon, color: 'error' }
  ];

  return (
    <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}>
      <Stack direction="row" spacing={3}>
        {items.map(({ key, label, icon: Icon, color }) => (
          <Box key={key} sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Button size="small" variant={cfg[key] ? 'contained' : 'outlined'} onClick={() => toggle(key)}>
              {label}
            </Button>
            <Icon fontSize="small" sx={{ mt: 0.5 }} color={cfg[key] ? color : 'disabled'} />
          </Box>
        ))}
      </Stack>
    </Box>
  );
}

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

      <NotificationBar cfg={normCfg.notifications} toggle={toggleNotification} />
    </Card>
  );
}
