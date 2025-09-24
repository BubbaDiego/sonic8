import React, { useMemo } from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  Typography,
  Stack,
  Box,
  Chip,
  Tooltip
} from '@mui/material';
import ShowChartTwoToneIcon from '@mui/icons-material/ShowChartTwoTone';
import MarketMovementCard from '../../components/MarketMovementCard';
import MonitorUpdateBar from './MonitorUpdateBar';

export default function MarketMonitorCard({ cfg, setCfg, live = {}, disabled = false }) {
  const normCfg = useMemo(() => {
    const notifications = {
      system: true,
      voice: true,
      sms: false,
      tts: true,
      ...(cfg?.notifications || {})
    };

    return { ...cfg, notifications };
  }, [cfg]);

  const toggleNotification = (key) => {
    setCfg((prev) => {
      const prevNotifications = {
        system: true,
        voice: true,
        sms: false,
        tts: true,
        ...(prev?.notifications || {})
      };

      return {
        ...prev,
        notifications: {
          ...prevNotifications,
          [key]: !Boolean(prevNotifications?.[key])
        }
      };
    });
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
            <Typography variant="h4" fontWeight={700} sx={{ fontSize: '1.1rem' }}>
              Market Movement Monitor
            </Typography>
            <ShowChartTwoToneIcon fontSize="medium" />
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

      <CardContent sx={{ p: 0, flex: '0 1 auto' }}>
        <MarketMovementCard cfg={cfg} setCfg={setCfg} live={live} disabled={disabled} />
      </CardContent>

      {/* pushes the bottom bar to the card edge */}
      <Box sx={{ flexGrow: 1 }} />

      {/* Single notifications bar (System / Voice / SMS / TTS) */}
      <MonitorUpdateBar cfg={normCfg.notifications} toggle={toggleNotification} sx={{ mx: 2, mb: 2 }} />

      {disabled && (
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            borderRadius: 1,
            pointerEvents: 'none',
            filter: 'grayscale(0.4)'
          }}
        />
      )}
    </Card>
  );
}
