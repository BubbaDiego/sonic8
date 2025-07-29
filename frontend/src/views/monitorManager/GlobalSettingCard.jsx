
import React, { useState, useEffect } from 'react';
import {
  Card, CardHeader, CardContent, Grid, Stack, TextField, Button,
  Typography, CircularProgress, Box
} from '@mui/material';

import SettingsTwoToneIcon from '@mui/icons-material/SettingsTwoTone';
import WaterDropIcon from '@mui/icons-material/WaterDrop';
import TrendingUpTwoToneIcon from '@mui/icons-material/TrendingUpTwoTone';
import ShowChartTwoToneIcon from '@mui/icons-material/ShowChartTwoTone';

/* ------------------------------------------------------------------------- */
function CircularCountdown({ remaining, total }) {
  const pct = (remaining / total) * 100;
  return (
    <Box sx={{ position: 'relative', display: 'inline-flex' }}>
      <CircularProgress value={pct} variant="determinate" size={80} thickness={4} />
      <Box
        sx={{
          top: 0,
          left: 0,
          bottom: 0,
          right: 0,
          position: 'absolute',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        <Typography variant="h6" component="div" color="text.secondary">
          {remaining}s
        </Typography>
      </Box>
    </Box>
  );
}

/* ------------------------------------------------------------------------- */
export default function GlobalSettingCard({
  cfg,
  setCfg,
  loop,
  setLoop,
  saveAll
}) {
  const [remaining, setRemaining] = useState(0);
  const [running, setRunning] = useState(false);

  const snooze = cfg.snooze_seconds ?? '';
  const loopSec = loop ?? '';

  // Track which monitors the Sonic loop should poll
  const monitors = {
    sonic: cfg.enabled_sonic ?? true,
    liquid: cfg.enabled_liquid ?? true,
    profit: cfg.enabled_profit ?? true,
    market: cfg.enabled_market ?? true
  };

  const start = () => {
    const sec = parseInt(snooze, 10);
    if (sec > 0) {
      setRemaining(sec);
      setRunning(true);
    }
  };

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          setRunning(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [running]);

  const onChange = (e) => {
    const { name, value } = e.target;
    setCfg((prev) => ({ ...prev, [name]: value }));
  };

  const toggleMonitor = (key) => {
    const field = `enabled_${key}`;
    setCfg((prev) => ({ ...prev, [field]: !prev[field] }));
  };

  const onLoopChange = (e) => setLoop(e.target.value);

  return (
    <Card variant="outlined" sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <CardHeader
        title={
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h4" fontWeight={600}>
              Sonic Monitor
            </Typography>
            <SettingsTwoToneIcon fontSize="small" />
          </Stack>
        }
      />
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={6}>
            <Stack spacing={2}>
              <TextField
                label={
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Typography>Sonic Loop</Typography>
                    <img src="/images/hedgehog_icon.png" width={16} alt="Loop" />
                  </Stack>
                }
                type="number"
                value={loopSec}
                onChange={onLoopChange}
              />
            </Stack>
          </Grid>
          <Grid item xs={6}>
            <Stack spacing={2}>
              <TextField
                label={
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Typography>Snooze</Typography>
                    <img src="/images/zzz_icon.png" width={16} alt="Zzz" />
                  </Stack>
                }
                type="number"
                name="snooze_seconds"
                value={snooze}
                onChange={onChange}
              />
              {running ? (
                <CircularCountdown remaining={remaining} total={snooze || 1} />
              ) : (
                <Button variant="outlined" onClick={start}>
                  Start Snooze Countdown
                </Button>
              )}
            </Stack>
          </Grid>
        </Grid>

        {/* Save-all lives here now */}
        <Box sx={{ mt: 3, textAlign: 'right' }}>
          <Button variant="contained" onClick={saveAll}>
            Save All
          </Button>
        </Box>

        {/* Monitor enable / disable buttons */}
        <Box sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
          <Stack direction="row" spacing={3}>
            {[
              { key: 'sonic',  label: 'Sonic',  icon: SettingsTwoToneIcon },
              { key: 'liquid', label: 'Liquid', icon: WaterDropIcon },
              { key: 'profit', label: 'Profit', icon: TrendingUpTwoToneIcon },
              { key: 'market', label: 'Market', icon: ShowChartTwoToneIcon }
            ].map(({ key, label, icon: Icon }) => (
              <Box key={key} sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Button
                  size="small"
                  variant={monitors[key] ? 'contained' : 'outlined'}
                  onClick={() => toggleMonitor(key)}
                >
                  {label}
                </Button>
                <Icon fontSize="small" sx={{ mt: 0.5 }} color={monitors[key] ? 'primary' : 'disabled'} />
              </Box>
            ))}
          </Stack>
        </Box>
      </CardContent>
    </Card>
  );
}
