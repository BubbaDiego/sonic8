
import React, { useMemo } from 'react';
import {
  Card, CardHeader, CardContent, Grid, Stack, TextField, Typography,
  Tooltip, Switch
} from '@mui/material';

import TrendingUpTwoToneIcon from '@mui/icons-material/TrendingUpTwoTone';

import MemoryIcon from '@mui/icons-material/Memory';
import RecordVoiceOverIcon from '@mui/icons-material/RecordVoiceOver';
import SmsIcon from '@mui/icons-material/Sms';
import CampaignIcon from '@mui/icons-material/Campaign';
import { Box, Button } from '@mui/material';

/* ------------------------------------------------------------------------- */
function NotificationBar({ cfg, toggle }) {
  const items = [
    { key: 'system', label: 'System', icon: MemoryIcon, color: 'info' },
    { key: 'voice', label: 'Voice', icon: RecordVoiceOverIcon, color: 'success' },
    { key: 'sms', label: 'SMS', icon: SmsIcon, color: 'warning' },
    { key: 'tts', label: 'TTS', icon: CampaignIcon, color: 'error' }
  ];

  return (
    <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center' }}>
      <Stack direction="row" spacing={3}>
        {items.map(({ key, label, icon: Icon, color }) => (
          <Box key={key} sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Button
              size="small"
              variant={cfg[key] ? 'contained' : 'outlined'}
              onClick={() => toggle(key)}
            >
              {label}
            </Button>
            <Icon fontSize="small" sx={{ mt: 0.5 }} color={cfg[key] ? color : 'disabled'} />
          </Box>
        ))}
      </Stack>
    </Box>
  );
}

/* ------------------------------------------------------------------------- */
export default function ProfitMonitorCard({ cfg, setCfg }) {
  const normCfg = useMemo(
    () => ({
      enabled: cfg.enabled ?? true,
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

  const handleChange = (e) => {
    const { name, value } = e.target;
    setCfg((prev) => ({ ...prev, [name]: value }));
  };

  const toggleNotification = (key) => {
    setCfg((prev) => ({
      ...prev,
      notifications: { ...prev.notifications, [key]: !prev.notifications[key] }
    }));
  };

  const handleEnabledChange = (e) =>
    setCfg((prev) => ({ ...prev, enabled: e.target.checked }));

  return (
    <Card variant="outlined" sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <CardHeader
        title={
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h4" fontWeight={600}>
              Profit Monitor
            </Typography>
            <TrendingUpTwoToneIcon fontSize="small" />
          </Stack>
        }
        action={
          <Tooltip title={normCfg.enabled ? 'Monitor enabled' : 'Monitor disabled'}>
            <Switch size="small" checked={normCfg.enabled} onChange={handleEnabledChange} />
          </Tooltip>
        }
      />
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={6}>
            <Stack spacing={2}>
              <TextField
                fullWidth
                label="PORTFOLIO HIGH ($)"
                name="portfolio_high"
                type="number"
                value={normCfg.portfolio_high ?? ''}
                onChange={handleChange}
              />
              <TextField
                fullWidth
                label="PORTFOLIO LOW ($)"
                name="portfolio_low"
                type="number"
                value={normCfg.portfolio_low ?? ''}
                onChange={handleChange}
              />
            </Stack>
          </Grid>
          <Grid item xs={6}>
            <Stack spacing={2}>
              <TextField
                fullWidth
                label="SINGLE HIGH ($)"
                name="single_high"
                type="number"
                value={normCfg.single_high ?? ''}
                onChange={handleChange}
              />
              <TextField
                fullWidth
                label="SINGLE LOW ($)"
                name="single_low"
                type="number"
                value={normCfg.single_low ?? ''}
                onChange={handleChange}
              />
            </Stack>
          </Grid>
        </Grid>

        <NotificationBar cfg={normCfg.notifications} toggle={toggleNotification} />
      </CardContent>
    </Card>
  );
}
