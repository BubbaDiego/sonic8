
import React, { useState, useEffect } from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  Grid,
  Stack,
  TextField,
  Button,
  IconButton,
  Typography,
  CircularProgress,
  Box,
  Divider,
  Chip,
  Switch,
  FormControlLabel,
  Tooltip
} from '@mui/material';

import SettingsTwoToneIcon from '@mui/icons-material/SettingsTwoTone';
import WaterDropIcon from '@mui/icons-material/WaterDrop';
import TrendingUpTwoToneIcon from '@mui/icons-material/TrendingUpTwoTone';
import ShowChartTwoToneIcon from '@mui/icons-material/ShowChartTwoTone';
import ShieldTwoToneIcon from '@mui/icons-material/ShieldTwoTone';
import { resetLiquidSnooze } from 'api/sonicMonitor';
import { refreshMonitorStatus } from 'api/monitorStatus';
import useSonicStatusPolling from 'hooks/useSonicStatusPolling';

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
export default function SonicMonitorCard({
  cfg,
  setCfg,
  loop,
  setLoop
}) {
  const [remaining, setRemaining] = useState(0);
  const [running, setRunning] = useState(false);
  const [nowTs, setNowTs] = useState(Date.now());

  const { snoozeEndTs } = useSonicStatusPolling();
  const snoozeEnd = typeof snoozeEndTs === 'number' ? snoozeEndTs : snoozeEndTs ? Date.parse(snoozeEndTs) : 0;
  const snoozeLeftMs = Math.max(0, (snoozeEnd || 0) - nowTs);
  const isSnoozed = snoozeLeftMs > 0;
  const fmtLeft = (ms) => {
    const s = Math.ceil(ms / 1000);
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${m}:${String(r).padStart(2, '0')}`;
  };

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

  const handleResetSnooze = async () => {
    try {
      await resetLiquidSnooze();
      refreshMonitorStatus();
      setRemaining(0);
      setRunning(false);
    } catch (err) {
      console.error('Failed to reset snooze', err);
    }
  };

  useEffect(() => {
    const id = setInterval(() => setNowTs(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

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

  const toggleSnoozePolicy = (on) => {
    setCfg((prev) => ({
      ...prev,
      snooze_seconds: on ? parseInt(prev?.snooze_seconds, 10) || 600 : 0
    }));
  };

  const onLoopChange = (e) => setLoop(e.target.value);

  return (
    <Card variant="outlined" sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <CardHeader
        title={
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h4" fontWeight={600} sx={{ fontSize: '1.1rem' }}>
              Sonic Monitor
            </Typography>
            <SettingsTwoToneIcon fontSize="small" />
          </Stack>
        }
        action={
          <Stack direction="row" spacing={1} alignItems="center">
            <Tooltip title="Master gate. Without Sonic enabled, nothing runs.">
              <Chip
                size="small"
                label={cfg?.enabled_sonic ? 'Enabled' : 'Disabled'}
                color={cfg?.enabled_sonic ? 'success' : 'default'}
                variant={cfg?.enabled_sonic ? 'filled' : 'outlined'}
                onClick={() => toggleMonitor('sonic')}
              />
            </Tooltip>
            <Chip
              size="small"
              label={isSnoozed ? `Snoozed ${fmtLeft(snoozeLeftMs)}` : 'Live'}
              color={isSnoozed ? 'warning' : 'info'}
              variant={isSnoozed ? 'filled' : 'outlined'}
            />
          </Stack>
        }
      />
      <CardContent>
        {/* Two‑by‑two control grid */}
        <Grid container spacing={2}>
          {/* ── Row 1 ───────────────────────────────── */}
          <Grid item xs={6}>
            <TextField
              fullWidth
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
          </Grid>
          <Grid item xs={6} sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
            {/* Save All button removed */}
          </Grid>

          {/* ── Row 2 ───────────────────────────────── */}
          <Grid item xs={6}>
            <TextField
              fullWidth
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
              helperText="0 disables snooze"
            />
          </Grid>
          <Grid
            item
            xs={6}
            sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 1 }}
          >
            {running ? (
              <CircularCountdown remaining={remaining} total={Number(snooze) || 1} />
            ) : (
              <>
                <Tooltip title="UI countdown only. Real snooze kicks in after an alert.">
                  <Button variant="outlined" onClick={start}>
                    Start Timer
                  </Button>
                </Tooltip>
                <FormControlLabel
                  control={
                    <Switch
                      checked={Number(snooze) > 0}
                      onChange={(e) => toggleSnoozePolicy(e.target.checked)}
                    />
                  }
                  label={Number(snooze) > 0 ? 'Snooze enabled' : 'Snooze disabled'}
                  sx={{ mr: 1 }}
                />
                <IconButton color="primary" onClick={handleResetSnooze}>
                  <ShieldTwoToneIcon />
                </IconButton>
              </>
            )}
          </Grid>
        </Grid>

        {/* divider stays, but toggle bar moves below the content */}
        <Divider sx={{ mt: 4, mb: 2 }} />
      </CardContent>

      {/* spacer forces the next box to the card's foot */}
      <Box sx={{ flexGrow: 1 }} />

      {/* ───────── Enable / disable toggles (framed) ───────── */}
      <Box
        sx={{
          mx: 2,
          mb: 2,
          p: 2,
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 1,
          backgroundColor: 'background.paper',
          display: 'flex',
          justifyContent: 'space-around',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: 3
        }}
      >
        {[
          { key: 'sonic',  label: 'Sonic',  icon: SettingsTwoToneIcon },
          { key: 'liquid', label: 'Liquid', icon: WaterDropIcon },
          { key: 'profit', label: 'Profit', icon: TrendingUpTwoToneIcon },
          { key: 'market', label: 'Market', icon: ShowChartTwoToneIcon }
        ].map(({ key, label, icon: Icon }) => (
          <Stack
            key={key}
            spacing={0.5}
            sx={{ minWidth: 64, alignItems: 'center' }}
          >
            <Button
              size="small"
              variant={monitors[key] ? 'contained' : 'outlined'}
              sx={{ px: 2, minWidth: 'auto' }}
              onClick={() => toggleMonitor(key)}
            >
              {label}
            </Button>
            <Icon fontSize="medium" color={monitors[key] ? 'primary' : 'disabled'} />
          </Stack>
        ))}
      </Box>
    </Card>
  );
}
