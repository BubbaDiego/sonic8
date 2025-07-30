import React, { useMemo } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  TextField,
  Button,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Typography,
  Stack,
  Box
} from '@mui/material';

import WaterDropIcon from '@mui/icons-material/WaterDrop';
import TuneTwoToneIcon from '@mui/icons-material/TuneTwoTone';
import InsightsTwoToneIcon from '@mui/icons-material/InsightsTwoTone';
import BlurCircularTwoToneIcon from '@mui/icons-material/BlurCircularTwoTone';

// Notification icons removed – handled by shared component

import MonitorUpdateBar from '../../components/MonitorUpdateBar';

import btcLogo from '/images/btc_logo.png';
import ethLogo from '/images/eth_logo.png';
import solLogo from '/images/sol_logo.png';

/* ------------------------------------------------------------------------- */
/*  Constants                                                                 */
/* ------------------------------------------------------------------------- */
const ASSETS = [
  { code: 'BTC', icon: btcLogo },
  { code: 'ETH', icon: ethLogo },
  { code: 'SOL', icon: solLogo }
];

/* ------------------------------------------------------------------------- */
/*  Main card                                                                 */
/* ------------------------------------------------------------------------- */
// Note: per-card enable switch removed – Sonic Monitor toggles instead
export default function LiquidationMonitorCard({ cfg, setCfg, blast = {}, nearest = {}, disabled = false }) {
  const normCfg = useMemo(
    () => ({
      thresholds: { BTC: '', ETH: '', SOL: '', ...(cfg.thresholds || {}) },
      blast_radius: blast || {},
      notifications: {
        system: true,
        voice: true,
        sms: false,
        tts: true,
        ...(cfg.notifications || {})
      },
      enabled: cfg.enabled ?? true
    }),
    [cfg, blast]
  );

  /* ----------------------- helpers --------------------------------------- */
  const handleThresholdChange = (asset) => (e) => {
    setCfg((prev) => ({
      ...prev,
      thresholds: { ...(prev.thresholds || {}), [asset]: e.target.value }
    }));
  };


  const applyBlast = (asset) => () => {
    const br = normCfg.blast_radius[asset];
    if (br == null) return;
    setCfg((prev) => ({
      ...prev,
      thresholds: { ...(prev.thresholds || {}), [asset]: br }
    }));
  };

  const getNearestObj = (code) => {
    const v = nearest[code];
    if (v == null) return { dist: '\u2014', side: '' };
    if (typeof v === 'number') return { dist: v, side: '' };
    return { dist: v.dist, side: v.side };
  };

  // Choose a reference radius for percentage and colour. Prefer the
  // API-supplied blast radius; fall back to the user-entered threshold so
  // the display is always meaningful.
  const refRadius = (code) => {
    const br = normCfg.blast_radius[code];
    const th = Number(normCfg.thresholds[code]);
    return typeof br === 'number' ? br : typeof th === 'number' ? th : null;
  };

  const getDistColour = (code) => {
    const d = getNearestObj(code).dist;
    const r = refRadius(code);
    if (typeof d !== 'number' || r == null) return 'text.primary';
    if (d > r) return 'success.main';
    if (d > r * 0.5) return 'warning.main';
    return 'error.main';
  };

  const fmtDistance = (code, val) => {
    if (val == null || val === '—') return val;
    return ['BTC', 'ETH'].includes(code) ? Math.round(val) : code === 'SOL' ? Number(val).toFixed(2) : val;
  };

  /* ----------------------------------------------------------------------- */
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
            <Typography variant="h4" fontWeight={600} sx={{ fontSize: '1.6rem' }}>
              Liquidation Monitor
            </Typography>
            <WaterDropIcon fontSize="small" color="primary" />
          </Stack>
        }
      />
      <CardContent>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>
                <Stack direction="row" spacing={0.5} alignItems="center">
                  <TuneTwoToneIcon fontSize="inherit" />
                  <Typography variant="subtitle2" fontWeight={700}>
                    Threshold
                  </Typography>
                </Stack>
              </TableCell>
              <TableCell>
                <Stack direction="row" spacing={0.5} alignItems="center">
                  <InsightsTwoToneIcon fontSize="inherit" />
                  <Typography variant="subtitle2" fontWeight={700}>
                    Current
                  </Typography>
                </Stack>
              </TableCell>
              <TableCell align="center">
                <Stack direction="row" spacing={0.5} justifyContent="center">
                  <BlurCircularTwoToneIcon fontSize="inherit" />
                  <Typography variant="subtitle2" fontWeight={700}>
                    Blast&nbsp;Radius
                  </Typography>
                </Stack>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {ASSETS.map(({ code, icon }) => {
              const { dist } = getNearestObj(code);
              return (
                <TableRow key={code}>
                  <TableCell sx={{ width: 160 }}>
                    <Stack direction="row" spacing={1.5} alignItems="center">
                      <img src={icon} width={22} alt={code} style={{ flexShrink: 0 }} />
                      <TextField
                        type="number"
                        size="small"
                        value={normCfg.thresholds[code]}
                        onChange={handleThresholdChange(code)}
                        sx={{ width: 110 }}
                      />
                    </Stack>
                  </TableCell>
                  <TableCell align="center" sx={{ width: 170 }}>
                    <Typography variant="body2" sx={{ fontWeight: 700 }}>
                      {/* plain number (theme text colour) */}
                      <Box component="span" color="text.primary">
                        {fmtDistance(code, dist)}
                      </Box>

                      {/* coloured percentage */}
                      {(() => {
                        const r = refRadius(code);
                        if (typeof dist !== 'number' || r == null) return null;
                        return (
                          <Box component="span" color={getDistColour(code)}>
                            {` (${((dist / r) * 100).toFixed(1)}%)`}
                          </Box>
                        );
                      })()}
                    </Typography>
                  </TableCell>
                  <TableCell align="center" sx={{ width: 100 }}>
                    <Button variant="outlined" size="small" sx={{ minWidth: 70 }} onClick={applyBlast(code)}>
                      {normCfg.blast_radius[code]?.toFixed(1) || '—'}
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>

        <MonitorUpdateBar
          cfg={normCfg.notifications}
          toggle={(k) =>
            setCfg((prev) => ({
              ...prev,
              notifications: { ...prev.notifications, [k]: !prev.notifications[k] }
            }))
          }
        />
      </CardContent>
    </Card>
  );
}
