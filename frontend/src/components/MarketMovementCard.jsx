import React, { useMemo } from 'react';
import {
  Box,
  Stack,
  Typography,
  TextField,
  MenuItem,
  Divider,
  Chip,
  Button
} from '@mui/material';
import axios from 'utils/axios';
import useSonicStatusPolling from 'hooks/useSonicStatusPolling';

export default function MarketMovementCard({ cfg = {}, setCfg, live = {}, disabled = false }) {
  const { sonicActive } = useSonicStatusPolling();

  const assets = useMemo(() => {
    const keys = Object.keys(cfg?.thresholds || {});
    return keys.length ? keys : ['SPX', 'BTC', 'ETH', 'SOL'];
  }, [cfg]);

  const rearm = String(cfg?.rearm_mode || 'ladder');

  const setRearm = (mode) => {
    setCfg((prev) => ({ ...prev, rearm_mode: mode }));
  };

  const getThr = (asset) => {
    const t = cfg?.thresholds?.[asset];
    if (t && typeof t === 'object') {
      return {
        delta: String(t.delta ?? ''),
        direction: String((t.direction || 'both')[0].toUpperCase() + (t.direction || 'both').slice(1))
      };
    }
    // legacy numeric shape
    return { delta: String(t ?? ''), direction: 'Both' };
  };

  const setThr = (asset, patch) => {
    setCfg((prev) => {
      const prevT = prev?.thresholds?.[asset];
      const asObj = prevT && typeof prevT === 'object' ? prevT : { delta: prevT ?? '' };
      const next = {
        ...(prev?.thresholds || {}),
        [asset]: {
          delta: Number(patch.delta ?? asObj.delta ?? 0),
          direction: String((patch.direction ?? asObj.direction ?? 'both')).toLowerCase()
        }
      };
      return { ...prev, thresholds: next };
    });
  };

  const resetAnchors = async () => {
    try {
      await axios.post('/api/monitor-settings/market/reset-anchors');
    } catch {}
  };

  return (
    <Box sx={{ p: 16 / 8, ...(disabled ? { opacity: 0.5, pointerEvents: 'none' } : {}) }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
        <Typography variant="subtitle2" sx={{ opacity: 0.9 }}>
          Trigger when price moves by the configured dollar amount from the last anchor.
        </Typography>
        <Stack direction="row" spacing={1} alignItems="center">
          <Chip
            size="small"
            label={sonicActive ? 'Sonic: Active' : 'Sonic: Idle'}
            color={sonicActive ? 'success' : 'default'}
            variant={sonicActive ? 'filled' : 'outlined'}
          />
          <TextField
            select
            size="small"
            label="Rearm"
            value={rearm[0].toUpperCase() + rearm.slice(1)}
            onChange={(e) => setRearm(String(e.target.value).toLowerCase())}
            sx={{ minWidth: 140 }}
          >
            <MenuItem value="Ladder">Ladder</MenuItem>
            <MenuItem value="Reset">Reset</MenuItem>
            <MenuItem value="Single">Single</MenuItem>
          </TextField>
          <Button size="small" variant="outlined" onClick={resetAnchors}>
            Reset Anchors
          </Button>
        </Stack>
      </Stack>

      <Divider sx={{ my: 1.25 }} />

      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
        <Typography variant="overline" sx={{ opacity: 0.7 }}>
          Asset
        </Typography>
        <Typography variant="overline" sx={{ opacity: 0.7 }}>
          Δ (USD)
        </Typography>
        <Typography variant="overline" sx={{ opacity: 0.7 }}>
          Direction
        </Typography>

        {assets.map((a) => {
          const t = getThr(a);
          return (
            <React.Fragment key={a}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Typography sx={{ fontWeight: 600 }}>{a}</Typography>
              </Box>
              <TextField
                size="small"
                value={t.delta}
                onChange={(e) => setThr(a, { delta: e.target.value })}
                inputProps={{ inputMode: 'decimal' }}
              />
              <TextField
                select
                size="small"
                value={t.direction}
                onChange={(e) => setThr(a, { direction: e.target.value })}
              >
                <MenuItem value="Both">Both</MenuItem>
                <MenuItem value="Up">Up</MenuItem>
                <MenuItem value="Down">Down</MenuItem>
              </TextField>
            </React.Fragment>
          );
        })}
      </Box>
      {/* NOTE: No notifications bar here. It lives in the wrapper card only. */}
    </Box>
  );
}
