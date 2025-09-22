import React, { useMemo } from 'react';
import { Card, CardHeader, CardContent, Grid, Stack, TextField, Typography } from '@mui/material';

import TrendingUpTwoToneIcon from '@mui/icons-material/TrendingUpTwoTone';

import { Box, Button } from '@mui/material';
import MonitorUpdateBar    from './MonitorUpdateBar';

/* ------------------------------------------------------------------------- */
/* ------------------------------------------------------------------------- */
export default function ProfitMonitorCard({ cfg, setCfg, disabled = false }) {
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

  const handleHighChange = (key) => (event) => {
    const value = Number(event.target.value || 0);
    setCfg((prev) => ({ ...prev, [key]: value }));
  };

  const toggleNotification = (key) => {
    setCfg((prev) => ({
      ...prev,
      notifications: { ...prev.notifications, [key]: !prev.notifications[key] }
    }));
  };


  return (
    <Card
      variant="outlined"
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        opacity: disabled ? 0.4 : 1,
        pointerEvents: disabled ? 'none' : 'auto',
        transition: 'opacity 0.2s ease'
      }}
    >
      <CardHeader
        title={
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h4" fontWeight={600} sx={{ fontSize: '1.1rem' }}>
              Profit Monitor
            </Typography>
            <TrendingUpTwoToneIcon fontSize="small" />
          </Stack>
        }
      />
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              type="number"
              label="Single ($)"
              value={Number(normCfg?.single_high ?? 0)}
              onChange={handleHighChange('single_high')}
              inputProps={{ min: 0 }}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              type="number"
              label="Portfolio ($)"
              value={Number(normCfg?.portfolio_high ?? 0)}
              onChange={handleHighChange('portfolio_high')}
              inputProps={{ min: 0 }}
            />
          </Grid>
        </Grid>

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
