
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
import MarketMovementCard from '../../components/MarketMovementCard';

/**
 * Simple wrapper so we have a named file‑level component. This keeps the
 * existing MarketMovementCard (which already shows 1h/6h/24h moves) while
 * aligning with the new card naming scheme requested by the user.
 */
export default function MarketMonitorCard({ cfg, setCfg, live = {}, disabled = false, monitors, setMonitors }) {
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
      <Divider sx={{ my: 1 }} />
      <Box sx={{ display: 'flex', justifyContent: 'space-around', pb: 2 }}>
        {['sonic', 'liquid', 'profit', 'market'].map((key) => (
          <Button
            key={key}
            size="small"
            variant={monitors[`enabled_${key}`] ? 'contained' : 'outlined'}
            onClick={() =>
              setMonitors((prev) => ({
                ...prev,
                [`enabled_${key}`]: !prev[`enabled_${key}`]
              }))
            }
          >
            {key.charAt(0).toUpperCase() + key.slice(1)}
          </Button>
        ))}
      </Box>
    </Card>
  );
}
