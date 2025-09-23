import React, { useMemo, useCallback } from 'react';
import axios from 'utils/axios';
import useSonicStatusPolling from 'hooks/useSonicStatusPolling';
import {
  Box,
  Stack,
  Typography,
  TextField,
  Select,
  MenuItem,
  Button,
  FormControl,
  InputLabel,
  Divider,
  Tooltip,
  Chip
} from '@mui/material';

/**
 * Inputs for the Market Movement Monitor.
 * Props:
 *   cfg:  monitor settings object
 *   setCfg: setter from MonitorManager (markDirty wrapper)
 *   live: optional live readout (unused for now)
 */
export default function MarketMovementCard({ cfg = {}, setCfg, live = {}, disabled = false }) {
  const { sonicActive } = useSonicStatusPolling();
  const assets = useMemo(() => {
    const keys = Object.keys(cfg?.thresholds || {});
    return keys.length ? keys : ['SPX', 'BTC', 'ETH', 'SOL'];
  }, [cfg]);

  const toggleNotify = useCallback(
    (key) => {
      setCfg((prev) => {
        const next = { ...(prev?.notifications || {}) };
        next[key] = !Boolean(next[key]);
        return { ...prev, notifications: next };
      });
    },
    [setCfg]
  );

  const thresholds = cfg?.thresholds || {};
  const rearmMode = cfg?.rearm_mode || 'ladder';

  const updateThreshold = (asset, patch) => {
    setCfg((prev) => ({
      ...prev,
      thresholds: {
        ...(prev.thresholds || {}),
        [asset]: {
          ...(prev.thresholds?.[asset] || { delta: 5, direction: 'both' }),
          ...patch
        }
      }
    }));
  };

  const updateRearm = (value) => {
    setCfg((prev) => ({ ...prev, rearm_mode: value }));
  };

  const resetAnchors = async () => {
    const { data } = await axios.post('/api/monitor-settings/market/reset-anchors');
    setCfg((prev) => {
      const nextAnchors = { ...(prev.anchors || {}) };
      Object.entries(data.anchors || {}).forEach(([asset, anchor]) => {
        if (anchor && typeof anchor === 'object') {
          nextAnchors[asset] = anchor;
        } else if (anchor !== undefined && anchor !== null) {
          nextAnchors[asset] = {
            value: Number(anchor),
            time: new Date().toISOString()
          };
        }
      });

      const currentAssets = new Set([
        ...Object.keys(nextAnchors),
        ...Object.keys(prev?.armed || {})
      ]);

      let armedValue = data.armed;
      if (typeof armedValue === 'boolean') {
        armedValue = Array.from(currentAssets).reduce(
          (acc, asset) => ({ ...acc, [asset]: armedValue }),
          {}
        );
      } else if (armedValue && typeof armedValue === 'object') {
        armedValue = { ...(prev.armed || {}), ...armedValue };
      } else {
        armedValue = prev.armed || {};
      }

      return {
        ...prev,
        anchors: nextAnchors,
        armed: armedValue
      };
    });
  };

  return (
    <Box sx={{ p: 2, ...(disabled ? { opacity: 0.5, pointerEvents: 'none' } : {}) }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
        <Typography variant="subtitle2">
          Trigger when price moves by the configured dollar amount from the last anchor.
        </Typography>
        <Stack direction="row" spacing={1}>
          <Chip
            size="small"
            label={sonicActive ? 'Sonic: Active' : 'Sonic: Idle'}
            color={sonicActive ? 'success' : 'default'}
            variant={sonicActive ? 'filled' : 'outlined'}
          />
          <FormControl size="small">
            <InputLabel id="rearm-label">Rearm</InputLabel>
            <Select
              labelId="rearm-label"
              label="Rearm"
              value={rearmMode}
              onChange={(e) => updateRearm(e.target.value)}
              sx={{ minWidth: 140 }}
            >
              <MenuItem value="ladder">Ladder</MenuItem>
              <MenuItem value="reset">Reset to Current</MenuItem>
              <MenuItem value="single">Single (disarm)</MenuItem>
            </Select>
          </FormControl>
          <Tooltip title="Set all anchors to current prices and re-arm">
            <Button variant="outlined" size="small" onClick={resetAnchors}>
              Reset Anchors
            </Button>
          </Tooltip>
        </Stack>
      </Stack>

      <Divider sx={{ mb: 1 }} />

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: '110px 1fr 160px',
          columnGap: 1.5,
          rowGap: 1.2,
          alignItems: 'center'
        }}
      >
        <Typography variant="overline">Asset</Typography>
        <Typography variant="overline">Δ (USD)</Typography>
        <Typography variant="overline">Direction</Typography>

        {assets.map((asset) => {
          const t = thresholds[asset] || { delta: 5, direction: 'both' };
          return (
            <React.Fragment key={asset}>
              <Typography sx={{ fontWeight: 600 }}>{asset}</Typography>

              <TextField
                size="small"
                type="number"
                inputProps={{ step: '0.01', min: 0 }}
                value={t.delta ?? ''}
                onChange={(e) =>
                  updateThreshold(asset, {
                    delta: e.target.value === '' ? '' : Number(e.target.value)
                  })
                }
              />

              <FormControl size="small">
                <Select
                  value={t.direction || 'both'}
                  onChange={(e) => updateThreshold(asset, { direction: e.target.value })}
                >
                  <MenuItem value="both">Both</MenuItem>
                  <MenuItem value="up">Up only</MenuItem>
                  <MenuItem value="down">Down only</MenuItem>
                </Select>
              </FormControl>
            </React.Fragment>
          );
        })}
      </Box>

      <Divider sx={{ my: 1.5 }} />

      <Box
        sx={{
          mt: 1,
          p: 1.25,
          bgcolor: 'primary.900',
          borderRadius: 1,
          border: '1px solid',
          borderColor: 'primary.800'
        }}
      >
        <Stack direction="row" spacing={1} alignItems="center" justifyContent="flex-start">
          <Button
            size="small"
            variant={cfg?.notifications?.system ? 'contained' : 'outlined'}
            onClick={() => toggleNotify('system')}
          >
            System
          </Button>
          <Button
            size="small"
            variant={cfg?.notifications?.voice ? 'contained' : 'outlined'}
            onClick={() => toggleNotify('voice')}
          >
            Voice
          </Button>
          <Button
            size="small"
            variant={cfg?.notifications?.sms ? 'contained' : 'outlined'}
            onClick={() => toggleNotify('sms')}
          >
            SMS
          </Button>
          <Button
            size="small"
            variant={cfg?.notifications?.tts ? 'contained' : 'outlined'}
            onClick={() => toggleNotify('tts')}
          >
            TTS
          </Button>
        </Stack>
      </Box>
    </Box>
  );
}

