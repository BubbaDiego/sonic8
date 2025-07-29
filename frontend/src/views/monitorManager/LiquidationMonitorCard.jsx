
import React, { useMemo } from 'react';
import {
  Card, CardContent, CardHeader, TextField, Button, Table, TableHead,
  TableRow, TableCell, TableBody, Typography, Tooltip, Switch, Stack, Box
} from '@mui/material';

import WaterDropIcon from '@mui/icons-material/WaterDrop';
import TuneTwoToneIcon from '@mui/icons-material/TuneTwoTone';
import InsightsTwoToneIcon from '@mui/icons-material/InsightsTwoTone';
import BlurCircularTwoToneIcon from '@mui/icons-material/BlurCircularTwoTone';

import MemoryIcon from '@mui/icons-material/Memory';
import RecordVoiceOverIcon from '@mui/icons-material/RecordVoiceOver';
import SmsIcon from '@mui/icons-material/Sms';
import CampaignIcon from '@mui/icons-material/Campaign';

import btcLogo from '/images/btc_logo.png';
import ethLogo from '/images/eth_logo.png';
import solLogo from '/images/sol_logo.png';

/* ------------------------------------------------------------------------- */
/*  Helper components                                                         */
/* ------------------------------------------------------------------------- */
function NotificationBar({ cfg, toggle }) {
  const items = [
    { key: 'system', label: 'System', icon: MemoryIcon, color: 'info' },
    { key: 'voice', label: 'Voice', icon: RecordVoiceOverIcon, color: 'success' },
    { key: 'sms', label: 'SMS', icon: SmsIcon, color: 'warning' },
    { key: 'tts', label: 'TTS', icon: CampaignIcon, color: 'error' }
  ];

  return (
    <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center' }}>
      <Stack direction="row" spacing={3}>
        {items.map(({ key, label, icon: Icon, color }) => (
          <Box key={key} sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Button
              size="small"
              variant={cfg[key] ? 'contained' : 'outlined'}
              onClick={() => toggle(key)}
            >
              {label}
            </Button>
            <Icon fontSize="small" sx={{ mt: 0.5 }} color={cfg[key] ? color : 'disabled'} />
          </Box>
        ))}
      </Stack>
    </Box>
  );
}

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
export default function LiquidationMonitorCard({ cfg, setCfg, blast = {}, nearest = {} }) {
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

  const handleEnabledChange = (e) => {
    setCfg((prev) => ({ ...prev, enabled: e.target.checked }));
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

  const getDistColour = (code) => {
    const br = normCfg.blast_radius[code];
    const d = getNearestObj(code).dist;
    if (typeof d !== 'number' || typeof br !== 'number') return 'text.primary';
    if (d > br) return 'success.main';
    if (d > br * 0.5) return 'warning.main';
    return 'error.main';
  };

  const fmtDistance = (code, val) => {
    if (val == null || val === '—') return val;
    return ['BTC', 'ETH'].includes(code)
      ? Math.round(val)
      : code === 'SOL'
      ? Number(val).toFixed(2)
      : val;
  };

  /* ----------------------------------------------------------------------- */
  return (
    <Card variant="outlined" sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <CardHeader
        title={
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h4" fontWeight={600}>
              Liquidation Monitor
            </Typography>
            <WaterDropIcon fontSize="small" color="primary" />
          </Stack>
        }
        action={
          <Tooltip title={normCfg.enabled ? 'Monitor enabled' : 'Monitor disabled'}>
            <Switch size="small" checked={normCfg.enabled} onChange={handleEnabledChange} />
          </Tooltip>
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
                    <Typography
                      variant="body2"
                      sx={{ fontWeight: 700 }}
                      color={getDistColour(code)}
                    >
                      {typeof dist === 'number' && typeof normCfg.blast_radius[code] === 'number'
                        ? `${fmtDistance(code, dist)} (${(
                            (dist / normCfg.blast_radius[code]) *
                            100
                          ).toFixed(1)}%)`
                        : fmtDistance(code, dist)}
                    </Typography>
                  </TableCell>
                  <TableCell align="center" sx={{ width: 100 }}>
                    <Button
                      variant="outlined"
                      size="small"
                      sx={{ minWidth: 70 }}
                      onClick={applyBlast(code)}
                    >
                      {normCfg.blast_radius[code]?.toFixed(1) || '—'}
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>

        <NotificationBar
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
