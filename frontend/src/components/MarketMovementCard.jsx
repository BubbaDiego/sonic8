import React, { useMemo } from 'react';
import axios from 'utils/axios';
import useSonicStatusPolling from 'hooks/useSonicStatusPolling';
import {
  Box, Stack, Typography, TextField, MenuItem, Divider, Chip, Button, Table, TableHead, TableBody, TableRow, TableCell
} from '@mui/material';
import Tooltip from '@mui/material/Tooltip';
import ShowChartTwoToneIcon from '@mui/icons-material/ShowChartTwoTone';
import MonitorUpdateBar from 'views/monitorManager/MonitorUpdateBar';

const toNumber = (v) => {
  const n = Number(String(v).replace(/,/g, ''));
  return Number.isFinite(n) ? n : NaN;
};
const formatDelta = (value) => (Number.isInteger(value) ? String(value) : value.toFixed(2));
const grouped = (value, { minimumFractionDigits = 0, maximumFractionDigits = 0 } = {}) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  return new Intl.NumberFormat('en-US', { useGrouping: true, minimumFractionDigits, maximumFractionDigits }).format(n);
};
// Anchor formatting similar to sonic6: SOL keeps fractional precision; others whole dollars
const formatAnchor = (symbol, value) => {
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  if (symbol === 'SOL') {
    return n >= 1 ? grouped(n, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                  : grouped(n, { minimumFractionDigits: 4, maximumFractionDigits: 4 });
  }
  return grouped(Math.round(n));
};

export default function MarketMovementCard({ cfg = {}, setCfg, live = {}, disabled = false }) {
  const { sonicActive } = useSonicStatusPolling();
  const assets = useMemo(() => {
    const keys = Object.keys(cfg?.thresholds || {});
    return keys.length ? keys : ['SPX', 'BTC', 'ETH', 'SOL'];
  }, [cfg]);

  const rearm = String(cfg?.rearm_mode || 'ladder');
  const setRearm = (mode) => setCfg((prev) => ({ ...prev, rearm_mode: mode }));

  const getThr = (asset) => {
    const t = cfg?.thresholds?.[asset];
    if (t && typeof t === 'object') {
      return { delta: String(t.delta ?? ''), direction: String(t.direction || 'both') };
    }
    // legacy numeric shape
    return { delta: String(t ?? ''), direction: 'both' };
  };
  const setThr = (asset, patch) => {
    setCfg((prev) => ({
      ...prev,
      thresholds: {
        ...(prev.thresholds || {}),
        [asset]: {
          ...(prev.thresholds?.[asset] || { delta: '', direction: 'both' }),
          ...patch
        }
      }
    }));
  };

  // Optional live anchors (from parent /api/market/latest). Resolve per-asset object shape.
  const anchors = live?.anchors || live?.prices || {};

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ px: 2, pt: 2, pb: 0.5, display: 'flex', alignItems: 'center', gap: 1 }}>
        <ShowChartTwoToneIcon color="primary" fontSize="small" />
        <Typography variant="h4" fontWeight={600} sx={{ fontSize: '1.1rem' }}>
          Market Monitor
        </Typography>
        <Chip
          size="small"
          sx={{ ml: 'auto' }}
          color={disabled ? 'default' : 'success'}
          variant={disabled ? 'outlined' : 'filled'}
          label={disabled ? 'Disabled' : (sonicActive ? 'Enabled' : 'Idle')}
        />
      </Box>
      <Divider />
      <Box sx={{ p: 2, pt: 1.5 }}>
        <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1 }}>
          <Typography variant="body2" sx={{ opacity: 0.8, fontWeight: 600 }}>Re-arm mode:</Typography>
          {['ladder', 'single', 'reset'].map((m) => (
            <Button key={m} size="small" variant={rearm === m ? 'contained' : 'outlined'} onClick={() => setRearm(m)}>{m[0].toUpperCase()+m.slice(1)}</Button>
          ))}
        </Stack>

        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Asset</TableCell>
              <TableCell>Δ (USD)</TableCell>
              <TableCell>Direction</TableCell>
              <TableCell>Anchor</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {assets.map((a) => {
              const t = getThr(a);
              return (
                <TableRow key={a}>
                  <TableCell sx={{ pl: 1.5, fontWeight: 600 }}>{a}</TableCell>
                  <TableCell>
                    <TextField
                      type="text"
                      size="small"
                      placeholder="0.00"
                      value={Number.isNaN(toNumber(t.delta)) ? t.delta : formatDelta(toNumber(t.delta))}
                      onChange={(e) => setThr(a, { delta: e.target.value })}
                      inputProps={{ inputMode: 'decimal' }}
                      onWheel={(e) => e.currentTarget.blur()}
                      sx={{ width: 120 }}
                    />
                  </TableCell>
                  <TableCell>
                    <TextField
                      size="small"
                      select
                      value={t.direction}
                      onChange={(e) => setThr(a, { direction: e.target.value })}
                      sx={{ width: 140 }}
                    >
                      <MenuItem value="both">Both</MenuItem>
                      <MenuItem value="up">Up</MenuItem>
                      <MenuItem value="down">Down</MenuItem>
                    </TextField>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ opacity: 0.85 }}>
                      {formatAnchor(a, anchors?.[a]?.value ?? anchors?.[a])}
                    </Typography>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </Box>
      <MonitorUpdateBar
        cfg={cfg?.notifications || {}}
        toggle={(key) =>
          setCfg((prev) => {
            const n = { ...(prev?.notifications || {}) };
            n[key] = !Boolean(n[key]);
            return { ...prev, notifications: n };
          })
        }
      />
    </Box>
  );
}

