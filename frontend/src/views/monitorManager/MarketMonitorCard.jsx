import React from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  Typography,
  Stack,
  Box,
  Button,
  Divider
} from '@mui/material';
import ShowChartTwoToneIcon from '@mui/icons-material/ShowChartTwoTone';
import SettingsTwoToneIcon from '@mui/icons-material/SettingsTwoTone';
import WaterDropIcon from '@mui/icons-material/WaterDrop';
import TrendingUpTwoToneIcon from '@mui/icons-material/TrendingUpTwoTone';

import MarketMovementCard from '../../components/MarketMovementCard';

export default function MarketMonitorCard({ cfg, setCfg, live = {}, disabled = false, monitors, setMonitors }) {
  const toggleMonitor = (key) => {
    setMonitors(prev => ({ ...prev, [`enabled_${key}`]: !prev[`enabled_${key}`] }));
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
            <Typography variant="h4" fontWeight={600}>Market Monitor</Typography>
            <ShowChartTwoToneIcon fontSize="small" />
          </Stack>
        }
      />
      <CardContent sx={{ p: 0 }}>
        <MarketMovementCard cfg={cfg} setCfg={setCfg} live={live} />
      </CardContent>

      <Box sx={{ flexGrow: 1 }} />
      <Divider sx={{ my: 2 }} />

      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-around',
          alignItems: 'flex-end',
          gap: 3,
          px: 1,
          pb: 2
        }}
      >
        {[
          { key: 'sonic', label: 'Sonic', icon: SettingsTwoToneIcon },
          { key: 'liquid', label: 'Liquid', icon: WaterDropIcon },
          { key: 'profit', label: 'Profit', icon: TrendingUpTwoToneIcon },
          { key: 'market', label: 'Market', icon: ShowChartTwoToneIcon }
        ].map(({ key, label, icon: Icon }) => (
          <Stack key={key} spacing={0.5} sx={{ minWidth: 64, alignItems: 'center' }}>
            <Button
              size="small"
              variant={monitors[`enabled_${key}`] ? 'contained' : 'outlined'}
              sx={{ px: 2, minWidth: 'auto' }}
              onClick={() => toggleMonitor(key)}
            >
              {label}
            </Button>
            <Icon fontSize="medium" color={monitors[`enabled_${key}`] ? 'primary' : 'disabled'} />
          </Stack>
        ))}
      </Box>
    </Card>
  );
}
