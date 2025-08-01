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
          <Grid item xs={6}>
            <TextField
              fullWidth
              label="PORTFOLIO HIGH ($)"
              name="portfolio_high"
              type="number"
              value={normCfg.portfolio_high ?? ''}
              onChange={handleChange}
            />
          </Grid>
          <Grid item xs={6}>
            <TextField
              fullWidth
              label="SINGLE HIGH ($)"
              name="single_high"
              type="number"
              value={normCfg.single_high ?? ''}
              onChange={handleChange}
            />
          </Grid>

          <Grid item xs={6}>
            <TextField
              fullWidth
              label="PORTFOLIO LOW ($)"
              name="portfolio_low"
              type="number"
              value={normCfg.portfolio_low ?? ''}
              onChange={handleChange}
            />
          </Grid>
          <Grid item xs={6}>
            <TextField
              fullWidth
              label="SINGLE LOW ($)"
              name="single_low"
              type="number"
              value={normCfg.single_low ?? ''}
              onChange={handleChange}
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
