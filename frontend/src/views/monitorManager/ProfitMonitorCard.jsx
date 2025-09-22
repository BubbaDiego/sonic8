import React, { useMemo } from 'react';
import { Card, CardHeader, CardContent, Grid, Stack, TextField, Typography, Chip, Tooltip, Box } from '@mui/material';

import TrendingUpTwoToneIcon from '@mui/icons-material/TrendingUpTwoTone';

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
      position_profit_usd: cfg.position_profit_usd ?? 50,
      portfolio_profit_usd: cfg.portfolio_profit_usd ?? 200,
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
        position: 'relative',
        opacity: disabled ? 0.35 : 1,
        pointerEvents: disabled ? 'none' : 'auto',
        transition: 'opacity 0.2s ease',
        borderLeft: '4px solid',
        borderLeftColor: disabled ? 'divider' : 'success.main'
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
        action={
          <Tooltip title="Enable/disable via Sonic Monitor">
            <Chip
              size="small"
              label={disabled ? 'Disabled' : 'Enabled'}
              color={disabled ? 'default' : 'success'}
              variant={disabled ? 'outlined' : 'filled'}
            />
          </Tooltip>
        }
      />
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              type="number"
              label="Position Profit (USD)"
              value={Number(normCfg?.position_profit_usd ?? 0)}
              onChange={handleHighChange('position_profit_usd')}
              inputProps={{ min: 0 }}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              type="number"
              label="Portfolio Profit (USD)"
              value={Number(normCfg?.portfolio_profit_usd ?? 0)}
              onChange={handleHighChange('portfolio_profit_usd')}
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

      {disabled && (
        <Box sx={{ position: 'absolute', inset: 0, borderRadius: 1, pointerEvents: 'none', filter: 'grayscale(0.4)' }} />
      )}
    </Card>
  );
}
